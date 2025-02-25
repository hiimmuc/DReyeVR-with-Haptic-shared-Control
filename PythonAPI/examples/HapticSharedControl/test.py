import json
from pathlib import Path
from turtle import speed

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bezier_path import *
from haptic_algo import *
from utils import *

plt.style.use("default")


# cspell: ignore bezier arctan xlabel figsize ylabel
def simulation(
    path, param, i_points, f_points, i_yaw, speed, init_steering_angle, vehicle_config, n_steps
):
    print("============================\nSimulation running\n============================")
    current_position = i_points
    # Haptic Shared Control Initialization
    haptic_control = HapticSharedControl(
        Cs=0.5,
        Kc=0.3,
        T=2,
        tp=1,
        speed=speed,
        desired_trajectory_params=param,
        vehicle_config=vehicle_config,
    )

    # Simulation Loop
    print("Starting Simulation")

    s_angleL = init_steering_angle
    s_angleR = init_steering_angle

    trajectory = [current_position]
    torques = []
    steering_angles_deg = [init_steering_angle]

    yaw_angles_deg = [i_yaw]  # if change sign of swa, change sign here

    # Calculate the torque at each step
    for i in range(n_steps):
        print("--------------------")
        print("Step:", i)

        torque, coef, desired_steering_angle_deg = haptic_control.calculate_torque(
            current_position=current_position,
            steering_angles_deg=[s_angleL, s_angleR],
            current_yaw_angle_deg=i_yaw,
        )

        next_position = haptic_control.rtp

        torques.append(torque)
        trajectory.append(next_position)

        steering_angles_deg.append(desired_steering_angle_deg)
        yaw_angles_deg.append(haptic_control.predict_yaw_angle_deg)

        s_angleL = np.clip(desired_steering_angle_deg, -47.95, 69.99)
        s_angleR = np.clip(desired_steering_angle_deg, -69.99, 47.95)
        # s_angleL = desired_steering_angle_deg
        # s_angleR = desired_steering_angle_deg
        i_yaw = haptic_control.predict_yaw_angle_deg
        current_position = next_position

    return path, trajectory, yaw_angles_deg


def plot_trajectory(paths, trajectories, yaw_angles_deg, recorded_path=None):
    # Extract trajectory points

    colors = ["red", "green", "orange"]
    # Plot the trajectory
    plt.figure(figsize=(8, 8))
    for i in range(len(paths)):
        trajectory = np.array(trajectories[i])
        x_points = trajectory[:, 0]
        y_points = trajectory[:, 1]

        plt.plot(paths[i][:, 0], paths[i][:, 1], "--", label="Bezier Path")
        for idx, point in enumerate(zip(paths[i][:, 0], paths[i][:, 1])):
            plt.plot(point[0], point[1], "o", color="blue")
        # plt.plot(path[0, 0], path[0, 1], "o", label="Start", color="blue")
        plt.plot(paths[i][-1, 0], paths[i][-1, 1], "o", label="End", color="green")

        # Plot the vehicle trajectory
        plt.plot(x_points, y_points, label="Predicted Path", color=colors[i])
        for idx, point in enumerate(zip(x_points, y_points)):
            plt.plot(point[0], point[1], "o", color=colors[i])
            plot_arrow(point[0], point[1], np.radians(yaw_angles_deg[i][idx]), 0.3, width=0.2)

    if recorded_path is not None:
        plt.plot(recorded_path[1], recorded_path[0], label="Recorded Path", color="orange")

    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Vehicle Path and Bezier Trajectory")

    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.axis("square")
    plt.show()


__file_path__ = Path(__file__).resolve().parent

# Load the vehicle configuration
with open(f"{__file_path__}/wheel_setting.json", "r") as f:
    vehicle_config = json.load(f)
vehicle = Vehicle(vehicle_config=vehicle_config)
R = vehicle.minimum_turning_radius
print("Minimum Turning Radius:", R, "m")

# define initial and final points
trial = str(input("Enter trial number 0(sample) L-R(1-6) R-L(8-12): "))
recorded_path = None
if trial == "0":
    P_0 = [-1.47066772, -13.22415039]  # [x, y] in carla -> [y, x] in matplotlib
    P_f = [-6.87066772, -21.62415039]
    P_d = [-0.37066772, -29.02415039]
    yaw_0 = 0
    yaw_d = 10
    yaw_f = 90
elif trial == "1":
    P_0 = [-2.13139057, -13.58492756]
    P_d = [-0.26648349, -27.88323593]
    P_f = [-8.6554842, -21.6907711]
    yaw_0 = 2.3220824999999934
    yaw_d = 29.3604774
    yaw_f = 105.7937202
elif trial == "2":
    P_0 = [-2.0546906, -15.14080429]
    P_d = [-0.16853675, -27.82400513]
    P_f = [-7.68998575, -21.31655693]
    yaw_0 = -1.9093017999999944
    yaw_d = 30.0815544
    yaw_f = 93.37516379
elif trial == "3":
    P_0 = [-2.33013225, -13.42747879]
    P_d = [-0.27527067, -27.43535042]
    P_f = [-7.19522429, -21.22905159]
    yaw_0 = -1.153442400000003
    yaw_d = 29.3213272
    yaw_f = 90.37275675
elif trial == "4":
    P_0 = [-2.59471703, -13.76090431]
    P_d = [-0.84754181, -27.41300201]
    P_f = [-7.63892126, -21.31984329]
    yaw_0 = 1.9469986000000006
    yaw_d = 25.734725999999995
    yaw_f = 90.29345572
elif trial == "5":
    P_0 = [-2.46604896, -12.84768295]
    P_d = [-0.76953948, -27.44445229]
    P_f = [-7.99046612, -21.05567169]
    yaw_0 = 3.3721313000000066
    yaw_d = 20.9653397
    yaw_f = 85.99301052
elif trial == "6":
    P_0 = [-2.68211842, -13.66109943]
    P_d = [-0.15471956, -27.84520721]
    P_f = [-7.58486843, -21.00892448]
    yaw_0 = 1.5638045999999974
    yaw_d = 31.523597700000003
    yaw_f = 85.90444851
elif trial == "8":
    P_0 = [-2.21546435, -31.60477066]
    P_d = [1.03518212, -18.32664871]
    P_f = [-7.7015214, -21.18217278]
    yaw_0 = 178.7055664
    yaw_d = 124.3087578
    yaw_f = 88.27893066
elif trial == "9":
    P_0 = [-1.3271035, -34.64346695]
    P_d = [1.54469788, -19.11241913]
    P_f = [-7.67417145, -21.5524559]
    yaw_0 = 182.4389496
    yaw_d = 125.65747833
    yaw_f = 88.90112317
elif trial == "10":
    P_0 = [-2.41052723, -31.86808777]
    P_d = [2.61411977, -16.33299065]
    P_f = [-7.40135479, -21.47801208]
    yaw_0 = 174.07925419999998
    yaw_d = 125.3021584
    yaw_f = 87.58251953
elif trial == "11":
    P_0 = [-1.99927211, -29.94470215]
    P_d = [2.38471651, -17.51079941]
    P_f = [-7.10684538, -21.3453064]
    yaw_0 = 181.86206049999998
    yaw_d = 121.4338913
    yaw_f = 88.89004517
elif trial == "12":
    P_0 = [-3.46834612, -30.75714493]
    P_d = [-0.9832288, -17.28814125]
    P_f = [-7.75748634, -21.73072243]
    yaw_0 = 177.7886658
    yaw_d = 147.1214333
    yaw_f = 89.86245729
else:
    print("Invalid trial number")
    exit()

if trial != "0":
    df = pd.read_excel(f"{__file_path__}/data/trials/trial{trial}.xlsx")
    x = df["LocationX"].to_list()
    y = df["LocationY"].to_list()
    yaw = df["RotationYaw"].to_list()
else:
    x = [P_0[0], P_d[0], P_f[0]]
    y = [P_0[1], P_d[1], P_f[1]]
    yaw = [yaw_0, yaw_d, yaw_f]
recorded_path = np.array([x, y])

# calculate the bezier path
print("Calculating Bezier Path")

n_points = 50
path1, control_points1, params1 = calculate_bezier_trajectory(
    start_pos=P_0[::-1],
    end_pos=P_d[::-1],
    start_yaw=yaw_0,
    end_yaw=yaw_d,
    n_points=n_points,
    turning_radius=R,
    show_animation=False,
)
# backward so reverse the yaw angle (+180)
path2, control_points2, params2 = calculate_bezier_trajectory(
    start_pos=P_d[::-1],
    end_pos=P_f[::-1],
    start_yaw=180 + yaw_d,
    end_yaw=180 + yaw_f,
    n_points=n_points,
    turning_radius=R,
    show_animation=False,
)

# Simulation Parameters
n_steps = 10
speed = 1.5
init_steering_angle = 10

# Run the simulation
path1, trajectory1, yaw_angles_deg1 = simulation(
    path=path1,
    param=params1,
    i_points=P_0[::-1],
    f_points=P_d[::-1],
    i_yaw=180 - yaw_0,
    speed=1 * speed,
    init_steering_angle=1 * init_steering_angle,
    vehicle_config=vehicle_config,
    n_steps=n_steps,
)


path2, trajectory2, yaw_angles_deg2 = simulation(
    path=path2,
    param=params2,
    i_points=P_d[::-1],
    f_points=P_f[::-1],
    i_yaw=180 - yaw_d,
    speed=-1 * speed,
    init_steering_angle=-1 * init_steering_angle,
    vehicle_config=vehicle_config,
    n_steps=n_steps,
)

# trajectory = np.concatenate((trajectory1, trajectory2[:]), axis=0)
# yaw_angles_deg = np.concatenate((yaw_angles_deg1, yaw_angles_deg2[:]), axis=0)
# path = np.concatenate((path1, path2[1:]), axis=0)

plot_trajectory(
    paths=[path1, path2],
    trajectories=[trajectory1, trajectory2],
    yaw_angles_deg=[yaw_angles_deg1, yaw_angles_deg2],
    recorded_path=recorded_path,
)
