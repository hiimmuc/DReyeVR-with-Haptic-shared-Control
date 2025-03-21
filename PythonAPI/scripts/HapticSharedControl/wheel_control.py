"""Using the Logitech G920 Driving Force Racing Wheel with Python
Notes for G920
    XInput vs. DirectInput: G920 is primarily an XInput device for Xbox/PC. In DirectInput mode (via Logitech drivers), it’s treated as a generic joystick, and mappings might differ from XInput’s standard layout. If you’re using XInput instead, DIJOYSTATE2 won’t apply—use XINPUT_STATE instead.
    Force Feedback: G920 supports force feedback in DirectInput via effects, not directly through lFX fields (set up separately with IDirectInputEffect).
    Customization: Use G HUB to adjust sensitivity or rotation (e.g., 900°), which affects lX scaling.
Troubleshooting
    No Input: Ensure G920 is in DirectInput mode and drivers are installed (G HUB or Logitech Gaming Software).
    Unexpected Values: Adjust axis ranges with DIPROPRANGE via SetProperty if defaults don’t match (-1000 to 1000).
    Button Misalignment: Test all buttons and adjust indices based on output.
"""

import sys

sys.path.append("../logidrivepy")
import ctypes
import gc
import time
from collections import defaultdict
from pprint import pprint

import numpy as np
import pandas as pd
from logidrivepy import LogitechController

# Ignore spelling errors for any unknown words in this script
# cspell:ignore logi logidrivepy DIJOYSTATE2 XINPUT_STATE IDirectInputEffect DIPROPRANGE

MAX_ANGLE_RANGE = 900
__current_time__ = time.time()


class WheelController:
    def __init__(self):
        self.controller_index = 0
        self.controller = LogitechController()
        self.controller.steering_initialize()

        self.controller.set_operating_range(index=self.controller_index, range=MAX_ANGLE_RANGE)
        print("\n---Logitech Controller Initialized---")
        print("Is connected:", self.controller.is_connected(index=self.controller_index))
        print(
            "Force feedback available:",
            self.controller.has_force_feedback(index=self.controller_index),
        )
        print(
            "Operating range:",
            self.controller.get_operating_range(index=self.controller_index, range=ctypes.c_int()),
        )

    def play_spring_force(
        self, offset_percentage, saturation_percentage=50, coefficient_percentage=100
    ):
        """
        Plays a spring force effect on the controller.
        This function updates the controller state and then plays a spring force effect
        with the specified parameters. The spring force effect is used to simulate a
        spring-like resistance on the controller.
        Args:
            offset_percentage (int): The offset percentage for the spring force effect (-100 -> 100).
            saturation_percentage (int, optional): The saturation percentage for the spring force effect (0 -> 100). Defaults to 50.
            coefficient_percentage (int, optional): The coefficient percentage for the spring force effect (0 -> 100). Defaults to 100.
        """

        self.controller.logi_update()  # update the controller state before any operation
        self.controller.play_spring_force(
            index=self.controller_index,
            offset_percentage=int(offset_percentage),
            saturation_percentage=int(saturation_percentage),
            coefficient_percentage=int(coefficient_percentage),
        )

    def stop_spring_force(self):
        """
        Stops the spring force feedback on the controller.
        This method updates the controller state and then stops the spring force
        feedback for the controller at the specified index.
        """

        self.controller.logi_update()
        self.controller.stop_spring_force(index=self.controller_index)

    def get_state_engines(self):
        """
                Retrieves the state of the engines from the controller.
                This method updates the controller state and retrieves various parameters
                related to the engine's state, such as position, rotation, velocity,
                acceleration, and force along different axes, as well as slider, POV,
                and button states.
                Returns:
                    dict: A dictionary containing the following keys and their corresponding values:
                        - "lX": int, position along the X-axis
                        - "lY": int, position along the Y-axis
                        - "lZ": int, position along the Z-axis (often unused)
                        - "lRx": int, rotation around the X-axis
                        - "lRy": int, rotation around the Y-axis
                        - "lRz": int, rotation around the Z-axis (Rudder or twist)
                        - "rglSlider": list of int, slider positions (L2/R2)
                        - "rgdwPOV": list of int, POV hat switch positions (rgdwPOV[0]: The D-pad. Reported in hundredths of a degree (0° = up, 9000 = right, 18000 = down, 27000 = left, -1 = centered). Logitech D-pads typically support 8 directions.
        Other POV entries (rgdwPOV[1-3]) are unused unless the device has multiple hats)
                        - "rgbButtons": list of int, button states (0: A, 1: B, 2: X, 3: Y, 4: L1, 5: R1, 6: Select, 7: Start, 8: Mode (Logitech button), 9: Left stick click, 10: Right stick click)
                        - "lVX": int, velocity along the X-axis
                        - "lVY": int, velocity along the Y-axis
                        - "lVZ": int, velocity along the Z-axis
                        - "lVRx": int, rotational velocity around the X-axis
                        - "lVRy": int, rotational velocity around the Y-axis
                        - "lVRz": int, rotational velocity around the Z-axis
                        - "rglVSlider": list of int, slider velocities
                        - "lAX": int, acceleration along the X-axis
                        - "lAY": int, acceleration along the Y-axis
                        - "lAZ": int, acceleration along the Z-axis
                        - "lARx": int, rotational acceleration around the X-axis
                        - "lARy": int, rotational acceleration around the Y-axis
                        - "lARz": int, rotational acceleration around the Z-axis
                        - "rglASlider": list of int, slider accelerations
                        - "lFX": int, force along the X-axis
                        - "lFY": int, force along the Y-axis
                        - "lFZ": int, force along the Z-axis
                        - "lFRx": int, rotational force around the X-axis
                        - "lFRy": int, rotational force around the Y-axis
                        - "lFRz": int, rotational force around the Z-axis
                        - "rglFSlider": list of int, slider forces
        """

        # cspell: ignore rgdw
        self.controller.logi_update()
        state_contents = self.controller.get_state_engines(self.controller_index).contents
        return {
            "lX": state_contents.lX,
            "lY": state_contents.lY,
            "lZ": state_contents.lZ,
            "lRx": state_contents.lRx,
            "lRy": state_contents.lRy,
            "lRz": state_contents.lRz,
            "rglSlider": list(state_contents.rglSlider),
            "rgdwPOV": list(state_contents.rgdwPOV),
            "rgbButtons": list(state_contents.rgbButtons),
            "lVX": state_contents.lVX,
            "lVY": state_contents.lVY,
            "lVZ": state_contents.lVZ,
            "lVRx": state_contents.lVRx,
            "lVRy": state_contents.lVRy,
            "lVRz": state_contents.lVRz,
            "rglVSlider": list(state_contents.rglVSlider),
            "lAX": state_contents.lAX,
            "lAY": state_contents.lAY,
            "lAZ": state_contents.lAZ,
            "lARx": state_contents.lARx,
            "lARy": state_contents.lARy,
            "lARz": state_contents.lARz,
            "rglASlider": list(state_contents.rglASlider),
            "lFX": state_contents.lFX,
            "lFY": state_contents.lFY,
            "lFZ": state_contents.lFZ,
            "lFRx": state_contents.lFRx,
            "lFRy": state_contents.lFRy,
            "lFRz": state_contents.lFRz,
            "rglFSlider": list(state_contents.rglFSlider),
        }

    def get_angle(self, translate=True):
        """
        Retrieves the angle of the wheel control.
        Args:
            translate (bool): If True, the angle is normalized to the range [-1.0, 1.0].
                              If False, the raw angle value is returned.
        Returns:
            float: The angle of the wheel control. If `translate` is True, the value is
                   normalized to the range [-1.0, 1.0]. If `translate` is False, the raw
                   angle value is returned.
        """
        self.controller.logi_update()
        if not translate:
            return self.get_state_engines()["lX"]
        else:
            return np.clip(self.get_state_engines()["lX"], -32767.0, 32767.0) / 32767.0

    def get_acceleration_pedal(self, translate=True):
        """
        Retrieves the current state of the acceleration pedal.
        Args:
            translate (bool): If True, translates the raw pedal value to a normalized range [0, 1].
                              If False, returns the raw pedal value.
        Returns:
            float: The state of the acceleration pedal. If `translate` is True, returns a normalized
                   value between 0 and 1. If `translate` is False, returns the raw value from the engine state.
        """
        self.controller.logi_update()
        if not translate:
            return self.get_state_engines()["lY"]
        else:
            return np.clip(self.get_state_engines()["lY"], -32767.0, 32767.0) / 32767.0

    def get_brake_pedal(self, translate=True):
        """
        Retrieves the current state of the brake pedal.
        Args:
            translate (bool): If True, translates the raw pedal value to a normalized range [0, 1].
                              If False, returns the raw pedal value.
        Returns:
            float: The state of the brake pedal. If `translate` is True, returns a normalized
                   value between 0 and 1. If `translate` is False, returns the raw value from the engine state.
        """
        self.controller.logi_update()
        if not translate:
            return self.get_state_engines()["lRZ"]
        else:
            return abs(self.get_state_engines()["lRZ"] - 32767.0) / 65535.0

    def get_buttons_pressed(self):
        """
        Retrieves and processes the current state of buttons on the steering wheel controller.
        This method reads the current state of the controller, processes the D-pad and button inputs,
        and returns a dictionary mapping button names to their current states.
        Returns:
            dict: A dictionary with the following keys:
                - "D-pad": str - Direction of the D-pad ("up", "right", "down", "left", or "center")
                - "A": bool - True if A button is pressed, False otherwise
                - "B": bool - True if B button is pressed, False otherwise
                - "X": bool - True if X button is pressed, False otherwise
                - "Y": bool - True if Y button is pressed, False otherwise
        Note:
            This method requires the controller to be initialized and connected.
            Uses `logi_update()` to get the latest input state from the controller.
        """

        def process_dpad(value):
            if value == 0:
                return "up"
            elif value == 9000:
                return "right"
            elif value == 18000:
                return "down"
            elif value == 27000:
                return "left"
            return "center"

        def process_buttons(value):
            if value != 0:
                return True
            return False

        self.controller.logi_update()

        states = self.get_state_engines()

        rgdwPOV = states["rgdwPOV"]
        rgbButtons = states["rgbButtons"]

        key_mapping = {
            "D-pad": process_dpad(rgdwPOV[0]),
            "A": process_buttons(rgbButtons[0]),
            "B": process_buttons(rgbButtons[1]),
            "X": process_buttons(rgbButtons[2]),
            "Y": process_buttons(rgbButtons[3]),
        }
        return key_mapping

    def exit(self):
        """
        Shuts down the steering controller and releases the resources.
        """
        self.controller.logi_update()
        self.controller.steering_shutdown()
        del self.controller
        gc.collect()


# --- Test functions ---
def record_states(controller, duration=10):
    """
    Records the states of the controller for a specified duration.
    Args:
        controller (WheelController): The wheel controller object.
        duration (int, optional): The duration for which to record the states. Defaults to 10.
    Returns:
        dict: A dictionary containing the recorded states.
    """
    states = {}
    start_time = time.time()
    while time.time() - start_time < duration:
        curr_state = controller.get_state_engines()
        if states == {}:
            states = curr_state
            continue

        for (curr_key, curr_values), (key, value) in zip(curr_state.items(), states.items()):
            if states[key] != curr_values and key != "lAZ":
                print(f"{key}: {value} --> {curr_values}")

        states = curr_state
        print("----")
        time.sleep(0.5)
    return


def spin_controller_full_test(controller):
    df = {}

    for sat in range(10, 101, 5):
        print(f"Saturation: {sat}", end=" | ")
        for coef in range(10, 101, 5):
            print(f"Coefficient: {coef}", end="\n")
            for offset in range(-100, 101, 1):
                print(f"Offset: {offset}", end="\n")
                # -i * 45 + 90
                # -4 ~ -18
                # -45 ~ -200
                controller.play_spring_force(
                    offset_percentage=offset,
                    saturation_percentage=sat,
                    coefficient_percentage=coef,
                )

                state = controller.get_state_engines()
                # export to csv
                df.setdefault("timestamp", []).append(str(time.time()))
                for key, value in vars(state).items():
                    df.setdefault(key, []).append(value)

                time.sleep(0.3)
            time.sleep(1)
        time.sleep(2)

    df = pd.DataFrame().from_dict(df)
    df.to_excel("spin_test_offset.xlsx", index=False)
    controller.stop_spring_force()


def spin_controller_forward_reverse_test(controller) -> None:
    def spin_test(controller, range_: list, step: int, forward: bool = True) -> dict:
        df = {}
        print("Waiting for 3 seconds")
        time.sleep(3)
        print("--------------------")
        start, end = range_ if forward else range_[::-1]
        end += 1 if forward else -1
        step = step if forward else -step
        for offset in range(start, end, step):
            print(f"//=====\nOffset: {offset}", end="\n")
            print(f"Angle before: {round(controller.get_angle() * 450, 1)}", end=" --> ")
            # play spring force
            controller.play_spring_force(
                offset_percentage=offset,
                saturation_percentage=100,
                coefficient_percentage=100,
            )

            time.sleep(2.0)
            state = controller.get_state_engines()

            # export to csv
            df.setdefault("timestamp", []).append(str(time.time()))
            for key, value in state.items():
                df.setdefault(key, []).append(value)

            print(f"Angle after: {round(controller.get_angle() * 450, 1)}")
            print(f"Acceleration: {controller.get_acceleration_pedal()}")
        return df

    data = {}
    print("\nForward test")
    temp = spin_test(controller, range_=(-100, 100), step=20, forward=True)
    controller.stop_spring_force()
    time.sleep(3)
    data = append_dict(data, temp)

    print("\nReverse test")
    temp = spin_test(controller, range_=(-100, 100), step=20, forward=False)
    controller.stop_spring_force()
    time.sleep(3)
    data = append_dict(data, temp)

    print("\nForward test")
    temp = spin_test(controller, range_=(-100, 100), step=20, forward=True)
    controller.stop_spring_force()
    time.sleep(3)
    data = append_dict(data, temp)

    print("\nReverse test")
    temp = spin_test(controller, range_=(-100, 100), step=20, forward=False)
    controller.stop_spring_force()
    time.sleep(3)
    data = append_dict(data, temp)

    # export to excel
    df = pd.DataFrame().from_dict(data)
    df.to_excel("spin_test_offset_forward0.xlsx", index=False)
    print("Forward-reverse test done.")
    time.sleep(1)
    controller.exit()
    
def spin_controller_state_test(controller):
    def spin_test(controller, offset, saturation_percentage, coefficient_percentage, time_step=0.01):
        df = {}
        print("--------------------")
        # *1 stay for a while
        print("#1: Waiting for 2 seconds")
        start_time = time.time()
        while time.time() - start_time < 2:
            time.sleep(time_step)
            pass
        print("---Current angle:", controller.get_angle() * (MAX_ANGLE_RANGE / 2))
        
        # *2 play spring force to reach the desired value
        print("#2: Playing spring force to reach the desired value", offset)
        # play spring force
        controller.play_spring_force(
            offset_percentage=int(offset),
            saturation_percentage=int(saturation_percentage),
            coefficient_percentage=int(coefficient_percentage),
        )
        if coefficient_percentage != 0:
            sign = coefficient_percentage / abs(coefficient_percentage)
        else:
            sign = 1

        # reach the value
        print("---Offset angle:", (offset / 100) * (MAX_ANGLE_RANGE / 2))
        error = abs((controller.get_angle() - sign * (offset/ 100)) * 450)
        start_time = time.time()
        while error > 1: # 1 degree
            df.setdefault("timestamp", []).append(str(time.time() - __current_time__))
            df.setdefault("State", []).append("Turning")
            df.setdefault("Offset", []).append(offset)
            df.setdefault("Saturation", []).append(saturation_percentage)
            df.setdefault("Coefficient", []).append(coefficient_percentage)
            df.setdefault("SWA (Measured)", []).append(controller.get_angle() * (MAX_ANGLE_RANGE / 2))
            time.sleep(time_step)
            error = abs((controller.get_angle() - sign * (offset/ 100)) * 450)
            
            if time.time() - start_time > 10:
                print("Timeout...", "Error:", error)
                break

        print("---Reach:", controller.get_angle() * (MAX_ANGLE_RANGE / 2))
        print("---Completed in", time.time() - start_time, "seconds")
        
        # *3 stay for a while
        print("#3: Waiting for 3 seconds to be stable")
        start_time = time.time()
        
        while time.time() - start_time < 3:
            df.setdefault("timestamp", []).append(str(time.time() - __current_time__))
            df.setdefault("State", []).append("Stabilizing")
            df.setdefault("Offset", []).append(offset)
            df.setdefault("Saturation", []).append(saturation_percentage)
            df.setdefault("Coefficient", []).append(coefficient_percentage)
            df.setdefault("SWA (Measured)", []).append(controller.get_angle() * (MAX_ANGLE_RANGE / 2))
            time.sleep(time_step)
        
        print("---Current angle:", controller.get_angle() * (MAX_ANGLE_RANGE / 2))
        
        # *4 return to the center
        print("#4: Returning to center")
        
        controller.play_spring_force(offset_percentage=int(0), 
                                     saturation_percentage=int(100), 
                                     coefficient_percentage=int((sign)*coefficient_percentage)) # reverse side
        #NOTE: sign of turning direction coef = sign of reversing direction coef
        
        start_time = time.time()
        while time.time() - start_time < 3:
            df.setdefault("timestamp", []).append(str(time.time() - __current_time__))
            df.setdefault("State", []).append("Centering")
            df.setdefault("Offset", []).append(0)
            df.setdefault("Saturation", []).append(100)
            df.setdefault("Coefficient", []).append(int((sign)*coefficient_percentage))
            df.setdefault("SWA (Measured)", []).append(controller.get_angle() * (MAX_ANGLE_RANGE / 2))
            time.sleep(time_step)

        print("---Return to angle:", controller.get_angle() * (MAX_ANGLE_RANGE / 2))
        return df
    
    # === Test ===
    data = {}
    controller.play_spring_force(offset_percentage=0, 
                                 saturation_percentage=100, 
                                 coefficient_percentage=100)
    time.sleep(3)
    coef_range = [-100, 100]
    offset_range = [-100, 100]
    sat_range = [10, 100]
    
    for offset in range(offset_range[0], offset_range[-1] + 1, 20):
        if offset == 0:
            continue
        for coef in range(coef_range[0], coef_range[-1] + 1, 20):
            if coef == 0:
                continue          
            for sat in range(sat_range[0], sat_range[-1] + 1, 10):
                print(f"\n>> Offset: {offset}% \t| Saturation: {sat}% \t| Coefficient: {coef}%")
                temp = spin_test(controller, offset, sat, coef, time_step=0.001) # 10ms
                data = append_dict(data, temp)
                time.sleep(3.0)
   
    controller.stop_spring_force() 
    
    
    df = pd.DataFrame().from_dict(data)
    df.to_excel("spin_test_stat_2.xlsx", index=False)
    print("State test done.")
    time.sleep(1)
    controller.exit()


def append_dict(d1, d2):
    for key, value in d2.items():
        d1.setdefault(key, []).extend(value)
    return d1


def spin_test():
    controller = WheelController()
    spin_controller_forward_reverse_test(controller)
    # spin_controller_full_test(controller)
    # spin_controller_state_test(controller)
    print("Spin test passed.\n")


def test_controller():
    controller = WheelController()
    record_states(controller, duration=100)
    controller.exit()
    print("Test passed.")


if __name__ == "__main__":
    # spin_test()
    test_controller()
    print("Done.")
