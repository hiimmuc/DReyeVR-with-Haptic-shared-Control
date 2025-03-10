import csv
import datetime
import os
import time
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np

from .utils import *

__current_time__ = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


class HapticSharedControl:
    debug = True

    def __init__(
        self,
        Cs=0.5,
        Kc=0.5,
        T=1.0,
        tp=1.0,
        speed=2,
        desired_trajectory_params=[],
        vehicle_config={},
        log: bool = True,
        simulation: bool = True,
    ):
        self.Cs = Cs
        self.Kc = Kc
        self.T = T

        self.tp = tp  # preview time
        self.speed = speed  # vehicle speed
        self.vehicle_config = vehicle_config  # vehicle configuration
        self.vehicle = Vehicle(vehicle_config)

        self.desired_trajectory_params = desired_trajectory_params
        self.desired_trajectory = desired_trajectory_params["path"]

        self.log = log
        self.simulation = simulation

        self.log_data = {
            "Time (t)": [],
            "[Measured] Current Position ~ r(t) (m)": {
                "X": [],
                "Y": [],
            },
            "[Measured] Steering Angles ~ delta(t) (deg)": {
                "FL": [],
                "FR": [],
            },
            "[Measured] Current Yaw Angle ~ Phi(t) (deg)": [],
            "[Measured] Steering Wheel Angle ~ Theta(t) (deg)": [],
            "[Computed] Turning Radius ~ R(delta) (m)": [],
            "[Computed] Vehicle Steering Angle ~ Delta(t) (deg)": [],
            "[Computed] Center of Rotation to WORLD ~ r_c(t) (m)": {
                "X": [],
                "Y": [],
            },
            "[Computed] Current Error to Trajectory ~ e(t)": [],
            "[Computed] Predicted Position ~ rtp(t) (m)": {
                "X": [],
                "Y": [],
            },
            "[Computed] Change of Yaw Angle ~ Delta_phi(t) (deg)": [],
            "[Computed] Predicted Yaw Angle ~ Phi_tp(t) (deg)": [],
            "[Computed] Predicted Error to Trajectory ~ eps_tp(t)": [],
            "[Computed] Desired Steering Wheel Angle ~ Theta_d(t) (deg)": [],
            "[Computed] Torque applied ~ Tau_das (N.m)": [],
        }

    def calculate_torque(
        self,
        current_position,
        steering_angles_deg,
        current_yaw_angle_deg,
        steering_wheel_angle_deg=None,
    ):
        """
        Calculate the torque for the haptic shared control system.
        Args:
            current_position : tuple or list
                The current position of the vehicle in the form (X, Y) in meters.
            steering_angles_deg : tuple or list
                The steering angles of the front left (FL) and front right (FR) wheels in degrees.
            current_yaw_angle_deg : float
                The current yaw angle of the vehicle in degrees.
            steering_wheel_angle_deg : float, optional
                The steering wheel angle in degrees. If not provided, it is assumed to be the same as the vehicle steering angle.
        Returns:
            tau_das : float
                The calculated torque in Newton-meters.
            coef : float
                The coefficient derived from the sigmoid function based on the error to the trajectory.
            desired_steering_angle_deg : float
                The desired steering wheel angle in degrees.
        """

        self.r = current_position  # measured position from carla
        self.phi = current_yaw_angle_deg  # measured yaw angle from carla
        self.deltas = steering_angles_deg  # measured steering angles from carla
        
        # *1 calculate the average steering angle and turning radius
        (
            self.turning_radius,
            self.vehicle_steering_angle_deg,
            self.center_of_rotation_to_vehicle,
        ) = self.vehicle.calc_turning_radius(steering_angles_deg).values()

        self.vehicle_steering_angle_rad = np.radians(self.vehicle_steering_angle_deg)

        # Check if the steering wheel angle is provided, otherwise use the vehicle steering angle
        if steering_wheel_angle_deg is None:
            self.steering_wheel_angle_deg = self.translate_sa_to_swa(
                self.vehicle_steering_angle_deg
            )
        else:
            self.steering_wheel_angle_deg = steering_wheel_angle_deg

        self.steering_wheel_angle_rad = np.radians(self.steering_wheel_angle_deg)

        # *2 Calculate the error of current position to the desired trajectory
        self.e_t, self.closest_pt_rt, self.closest_pt_rt_idx = self.distance_to_trajectory(
            current_position
        )

        # *3 Calculate the previewed driver model
        self.theta_d_rad = self.preview_driver_model(current_position, current_yaw_angle_deg)
        self.theta_d_deg = np.degrees(self.theta_d_rad)

        # *4 Calculate the torque
        self.tau_das = -(self.Cs * self.e_t) * (self.steering_wheel_angle_rad - self.theta_d_rad)
        # Calculate the coefficient based on the sigmoid function
        coef = sigmoid(self.Cs * self.e_t)
        desired_steering_wheel_angle_deg = self.theta_d_deg

        # Log the data for debugging
        self.logging()

        return self.tau_das, coef, desired_steering_wheel_angle_deg

    def preview_driver_model(self, current_position, current_yaw_angle_deg, method="simple"):
        """
        Predicts the desired steering angle based on the current position and yaw angle of the vehicle.
        Args:
            current_position (tuple): The current position of the vehicle as (x, y) coordinates.
            current_yaw_angle_deg (float): The current yaw angle of the vehicle in degrees.
            method (str, optional): The method to use for calculating the desired steering angle.
                                    Options are "simple" or "complex". Defaults to "simple".
        Returns:
            float: The desired steering angle in radians.
        """

        # *3.1 Predict the position of the vehicle at the preview time
        self.rtp = self.predict_position(
            current_position=current_position,
            current_yaw_angle_deg=current_yaw_angle_deg,
            vehicle_steering_angle_deg=self.vehicle_steering_angle_deg,
        )

        # *3.2 Calculate the error between desired trajectory and predicted position with tp[s] ahead
        # NOTE: check the sign of the error fn
        epsilon_tp_t, self.closest_pt_rtp, self.closest_pt_rtp_idx = self.distance_to_trajectory(
            self.rtp
        )
        self.epsilon_tp_t = self.get_sign_of_error(self.rtp) * epsilon_tp_t

        # *3.3 Calculate the desired steering angle
        if method == "simple":
            theta_d_rad = self.Kc * self.epsilon_tp_t + self.steering_wheel_angle_rad
        else:
            # ?... development in progress
            theta_d_rad_curr = self.steering_wheel_angle_rad
            theta_d_rad_next = None
            update_frequency = 60  # 100 Hz
            d_t = 1 / update_frequency  # 0.01 s
            for _ in range(update_frequency):
                theta_d_rad_next = (
                    self.Kc * self.epsilon_tp_t + ((self.T / d_t) - 1) * theta_d_rad_curr
                ) * (d_t / self.T)
                theta_d_rad_curr = theta_d_rad_next
            theta_d_rad = theta_d_rad_next

        return theta_d_rad

    def predict_position(
        self,
        current_position: list,
        current_yaw_angle_deg: float,
        vehicle_steering_angle_deg: float,
    ) -> list:
        """
        Predicts the future position of the vehicle based on the current position and yaw angle.
        Args:
            current_position (array-like): The current position of the vehicle in world coordinates [x, y].
            current_yaw_angle_deg (float): The current yaw angle of the vehicle in degrees.
        Returns:
            numpy.ndarray: The predicted position of the vehicle in world coordinates [x, y].
        """

        current_yaw_angle_rad = np.radians(current_yaw_angle_deg)
        vehicle_steering_angle_rad = np.radians(vehicle_steering_angle_deg)

        # vehicle coordinates, origin at the center of mass
        # define rotation direction for the vehicle
        # TODO (fixme): Check if the center of rotation is correct, from left to right and from right to left

        self.rotating_direction = np.sin(vehicle_steering_angle_rad) / np.abs(
            np.sin(vehicle_steering_angle_rad)
        )  #  -1 if clockwise, 1 if counter-clockwise

        # First calculate the center of rotation to the vehicle
        center_of_rotation_to_vehicle = self.center_of_rotation_to_vehicle

        # *1 transform the vehicle coordinates to the global coordinates
        # -- rotate current_yaw_angle_rad - np.pi / 2
        # -- shift with vector current_position
        self.center_of_rotation_to_world = rotation_matrix_cw(
            current_yaw_angle_rad - np.pi / 2
        ).dot(center_of_rotation_to_vehicle)
        +np.array(current_position)

        # *2 calculate the predicted position
        # -- calculate the delta_phi_rad
        # -- calculate the predicted yaw angle
        # -- calculate the predicted position

        self.delta_phi_rad = self.rotating_direction * self.speed * self.tp / self.turning_radius
        self.delta_phi_deg = np.degrees(self.delta_phi_rad)

        self.predict_yaw_angle_rad = current_yaw_angle_rad - self.delta_phi_rad
        self.predict_yaw_angle_deg = np.degrees(self.predict_yaw_angle_rad)

        predicted_position_in_world = (
            self.center_of_rotation_to_world
            + self.turning_radius
            * np.array(
                [
                    np.cos(
                        self.predict_yaw_angle_rad
                        - vehicle_steering_angle_rad
                        + self.rotating_direction * np.pi / 2
                    ),
                    np.sin(
                        self.predict_yaw_angle_rad
                        - vehicle_steering_angle_rad
                        + self.rotating_direction * np.pi / 2
                    ),
                ]
            )
        )

        return predicted_position_in_world

    def distance_to_trajectory(self, position):
        """
        Calculate the distance from a given position to the desired trajectory.
        This method finds the closest point on the desired trajectory to the given position
        and calculates the distance between them. It also prints the index of the closest point
        for debugging purposes.
        Args:
            position (tuple): The (x, y) coordinates of the current position.
        Returns:
            float: The distance from the given position to the closest point on the desired trajectory.
        """

        # More robust distance calculation by checking multiple points
        min_dist = float("inf")
        closest_point, idx = find_closest_point(position, self.desired_trajectory)
        return min(dist(position, closest_point), min_dist), closest_point, idx

    def get_sign_of_error(self, position):

        p1 = position
        _, pt_index = find_closest_point(p1, self.desired_trajectory)

        p2, p3 = self.desired_trajectory_params["tangent"][pt_index]
        angle_rad = getAngle(p1, p2, p3, degrees=False)

        return -(self.speed / np.abs(self.speed)) * (np.sin(angle_rad) / abs(np.sin(angle_rad)))

    def translate_sa_to_swa(self, sa_deg):
        """
        Translate the steering angle to the steering wheel angle.
        Args:
            sa_deg (float): The steering angle in degrees.
        Returns:
            float: The steering wheel angle in degrees.
        """
        if not self.simulation:
            return linear_fn(slope=28.836080132923243, intercept=-0.3699660038416528)(sa_deg)
        return linear_fn(1, 0)(sa_deg)

    def translate_swa_to_sa(self, swa_deg):
        """
        Translate the steering wheel angle to the steering angle.
        Args:
            swa_deg (float): The steering wheel angle in degrees.
        Returns:
            float: The steering angle in degrees.
        """
        if not self.simulation:
            return linear_fn(slope=0.034624741865409744, intercept=0.012729044962266822)(swa_deg)
        return linear_fn(1, 0)(swa_deg)

    def logging(self):
        """
        Log the data for debugging purposes.
        """
        print("----------------------")
        self.log_data["Time (t)"].append(time.time())
        self.log_data["[Measured] Current Position ~ r(t) (m)"]["X"].append(self.r[0])
        self.log_data["[Measured] Current Position ~ r(t) (m)"]["Y"].append(self.r[1])

        self.log_data["[Measured] Steering Angles ~ delta(t) (deg)"]["FL"].append(self.deltas[0])
        self.log_data["[Measured] Steering Angles ~ delta(t) (deg)"]["FR"].append(self.deltas[1])
        self.log_data["[Measured] Current Yaw Angle ~ Phi(t) (deg)"].append(self.phi)
        self.log_data["[Measured] Steering Wheel Angle ~ Theta(t) (deg)"].append(
            self.steering_wheel_angle_deg
        )
        self.log_data["[Computed] Turning Radius ~ R(delta) (m)"].append(self.turning_radius)
        self.log_data["[Computed] Vehicle Steering Angle ~ Delta(t) (deg)"].append(
            self.vehicle_steering_angle_deg
        )
        self.log_data["[Computed] Current Error to Trajectory ~ e(t)"].append(self.e_t)
        self.log_data["[Computed] Predicted Position ~ rtp(t) (m)"]["X"].append(self.rtp[0])
        self.log_data["[Computed] Predicted Position ~ rtp(t) (m)"]["Y"].append(self.rtp[1])

        self.log_data["[Computed] Change of Yaw Angle ~ Delta_phi(t) (deg)"].append(
            self.delta_phi_deg
        )

        self.log_data["[Computed] Center of Rotation to WORLD ~ r_c(t) (m)"]["X"].append(
            self.center_of_rotation_to_world[0]
        )
        self.log_data["[Computed] Center of Rotation to WORLD ~ r_c(t) (m)"]["Y"].append(
            self.center_of_rotation_to_world[1]
        )

        self.log_data["[Computed] Predicted Yaw Angle ~ Phi_tp(t) (deg)"].append(
            self.predict_yaw_angle_deg
        )
        self.log_data["[Computed] Predicted Error to Trajectory ~ eps_tp(t)"].append(
            self.epsilon_tp_t
        )

        self.log_data["[Computed] Desired Steering Wheel Angle ~ Theta_d(t) (deg)"].append(
            self.theta_d_deg
        )
        self.log_data["[Computed] Torque applied ~ Tau_das (N.m)"].append(self.tau_das)

        if self.debug:
            print("Logging data...")
            keys = list(self.log_data.keys())
            values = list(self.log_data.values())

            for i in range(len(keys)):
                if type(values[i]) == dict:
                    print(f"{keys[i]}:")
                    for sub_key, sub_value in values[i].items():
                        print(f"    {sub_key}: {sub_value[-1]}")
                else:
                    print(f"{keys[i]}: {(values[i][-1])}")

        if self.log:
            self.save_log()

    def save_log(self):
        """
        Save the log data to a CSV file.
        
        The method creates a CSV file if it doesn't exist, writing headers only once.
        It then appends the latest data point to the file each time it's called.
        """
        file_path = f"./logs/haptic_shared_control_log_{__current_time__}.csv"
        file_exists = os.path.isfile(file_path)
        
        # Prepare the data structure
        # For nested dictionaries, flatten the structure for CSV format
        headers = []
        row_data = {}
        
        for key, value in self.log_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    column_name = f"{key}_{sub_key}"
                    headers.append(column_name)
                    # Get the last value if available
                    if sub_value and len(sub_value) > 0:
                        row_data[column_name] = sub_value[-1]
                    else:
                        row_data[column_name] = None
            else:
                headers.append(key)
                # Get the last value if available
                if value and len(value) > 0:
                    row_data[key] = value[-1]
                else:
                    row_data[key] = None
        
        # Write to file
        with open(file_path, 'a', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            
            # Write header only if the file is newly created
            if not file_exists:
                writer.writeheader()
            
            # Write the latest data point
            writer.writerow(row_data)
            
        # Optional: Log that data was successfully saved
        if self.debug:
            print(f"Log data saved to {file_path}")


if __name__ == "__main__":
    pass
