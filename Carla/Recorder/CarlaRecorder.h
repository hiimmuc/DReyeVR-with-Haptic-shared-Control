// Copyright (c) 2017 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#pragma once

// #include "GameFramework/Actor.h"
#include <fstream>

#include "Carla/Actor/ActorDescription.h"

#include "CarlaRecorderTraficLightTime.h"
#include "CarlaRecorderPhysicsControl.h"
#include "CarlaRecorderPlatformTime.h"
#include "CarlaRecorderBoundingBox.h"
#include "CarlaRecorderKinematics.h"
#include "CarlaRecorderLightScene.h"
#include "CarlaRecorderLightVehicle.h"
#include "CarlaRecorderAnimVehicle.h"
#include "CarlaRecorderAnimWalker.h"
#include "CarlaRecorderCollision.h"
#include "CarlaRecorderEventAdd.h"
#include "CarlaRecorderEventDel.h"
#include "CarlaRecorderEventParent.h"
#include "CarlaRecorderFrames.h"
#include "CarlaRecorderInfo.h"
#include "CarlaRecorderPosition.h"
#include "CarlaRecorderQuery.h"
#include "CarlaRecorderState.h"
#include "CarlaRecorderWeather.h"
#include "CarlaReplayer.h"

// DReyeVR includes
#include "DReyeVRRecorder.h"
#include "Carla/Sensor/DReyeVRData.h"

#include "CarlaRecorder.generated.h"

class AActor;
class UCarlaEpisode;
class ACarlaWheeledVehicle;
class UCarlaLight;
class ATrafficSignBase;
class ATrafficLightBase;

#define DREYEVR_PACKET_ID 139
#define DREYEVR_CUSTOM_ACTOR_PACKET_ID 140
#define DREYEVR_CONFIG_FILE_PACKET_ID 141

enum class CarlaRecorderPacketId : uint8_t
{
  FrameStart = 0,
  FrameEnd,
  EventAdd,
  EventDel,
  EventParent,
  Collision,
  Position,
  State,
  AnimVehicle,
  AnimWalker,
  VehicleLight,
  SceneLight,
  Kinematics,
  BoundingBox,
  PlatformTime,
  PhysicsControl,
  TrafficLightTime,
  TriggerVolume,
  Weather,
  // "We suggest to use id over 100 for user custom packets, because this list will keep growing in the future"
  DReyeVR = DREYEVR_PACKET_ID,                         // our custom DReyeVR packet (for raw sensor data)
  DReyeVRCustomActor = DREYEVR_CUSTOM_ACTOR_PACKET_ID, // custom DReyeVR actors (not raw sensor data)
  DReyeVRConfigFile = DREYEVR_CONFIG_FILE_PACKET_ID    // DReyeVR configuration files (parameters)
};

/// Recorder for the simulation
UCLASS()
class CARLA_API ACarlaRecorder : public AActor
{
  GENERATED_BODY()

public:

  ACarlaRecorder(void);
  ACarlaRecorder(const FObjectInitializer &InObjectInitializer);

  // enable / disable
  bool IsEnabled(void)
  {
    return Enabled;
  }
  void Enable(void);

  void Disable(void);

  // start / stop
  std::string Start(std::string Name, FString MapName, bool AdditionalData = false);

  void Stop(void);

  void Clear(void);

  void Write(double DeltaSeconds);

  // events
  void AddEvent(const CarlaRecorderEventAdd &Event);

  void AddEvent(const CarlaRecorderEventDel &Event);

  void AddEvent(const CarlaRecorderEventParent &Event);

  void AddCollision(AActor *Actor1, AActor *Actor2);

  void AddPosition(const CarlaRecorderPosition &Position);

  void AddState(const CarlaRecorderStateTrafficLight &State);

  void AddAnimVehicle(const CarlaRecorderAnimVehicle &Vehicle);

  void AddAnimWalker(const CarlaRecorderAnimWalker &Walker);

  void AddLightVehicle(const CarlaRecorderLightVehicle &LightVehicle);

  void AddEventLightSceneChanged(const UCarlaLight* Light);

  void AddKinematics(const CarlaRecorderKinematics &ActorKinematics);

  void AddBoundingBox(const CarlaRecorderActorBoundingBox &ActorBoundingBox);

  void AddTriggerVolume(const ATrafficSignBase &TrafficSign);

  void AddPhysicsControl(const ACarlaWheeledVehicle& Vehicle);

  void AddTrafficLightTime(const ATrafficLightBase& TrafficLight);

  void AddWeather(const FWeatherParameters& WeatherParams);

  // set episode
  void SetEpisode(UCarlaEpisode *ThisEpisode)
  {
    Episode = ThisEpisode;
    Replayer.SetEpisode(ThisEpisode);
  }

  void CreateRecorderEventAdd(
      uint32_t DatabaseId,
      uint8_t Type,
      const FTransform &Transform,
      FActorDescription ActorDescription);

  // replayer
  CarlaReplayer *GetReplayer(void)
  {
    return &Replayer;
  }

  // queries
  std::string ShowFileInfo(std::string Name, bool bShowAll = false);
  std::string ShowFileCollisions(std::string Name, char Type1, char Type2);
  std::string ShowFileActorsBlocked(std::string Name, double MinTime = 30, double MinDistance = 10);

  // replayer
  std::string ReplayFile(std::string Name, double TimeStart, double Duration,
      uint32_t FollowId, bool ReplaySensors);
  void SetReplayerTimeFactor(double TimeFactor);
  void SetReplayerIgnoreHero(bool IgnoreHero);
  void StopReplayer(bool KeepActors = false);

  void Ticking(float DeltaSeconds);

private:

  bool Enabled;   // enabled or not

  // enabling this records additional data (kinematics, bounding boxes, etc)
  bool bAdditionalData = false;

  uint32_t NextCollisionId = 0;

  // files
  std::ofstream File;

  UCarlaEpisode *Episode = nullptr;

  // structures
  CarlaRecorderInfo Info;
  CarlaRecorderFrames Frames;
  CarlaRecorderEventsAdd EventsAdd;
  CarlaRecorderEventsDel EventsDel;
  CarlaRecorderEventsParent EventsParent;
  CarlaRecorderCollisions Collisions;
  CarlaRecorderPositions Positions;
  CarlaRecorderStates States;
  CarlaRecorderAnimVehicles Vehicles;
  CarlaRecorderAnimWalkers Walkers;
  CarlaRecorderLightVehicles LightVehicles;
  CarlaRecorderLightScenes LightScenes;
  CarlaRecorderActorsKinematics Kinematics;
  CarlaRecorderActorBoundingBoxes BoundingBoxes;
  CarlaRecorderActorTriggerVolumes TriggerVolumes;
  CarlaRecorderPlatformTime PlatformTime;
  CarlaRecorderPhysicsControls PhysicsControls;
  CarlaRecorderTrafficLightTimes TrafficLightTimes;
  CarlaRecorderWeathers Weathers;
  DReyeVRDataRecorders<DReyeVR::AggregateData, DREYEVR_PACKET_ID> DReyeVRAggData;
  DReyeVRDataRecorders<DReyeVR::CustomActorData, DREYEVR_CUSTOM_ACTOR_PACKET_ID> DReyeVRCustomActorData;
  DReyeVRDataRecorders<DReyeVR::ConfigFileData, DREYEVR_CONFIG_FILE_PACKET_ID> DReyeVRConfigFileData;

  // replayer
  CarlaReplayer Replayer;

  // query tools
  CarlaRecorderQuery Query;

  void AddExistingActors(void);
  void AddStartingWeather(void);
  void AddActorPosition(FCarlaActor *CarlaActor);
  void AddWalkerAnimation(FCarlaActor *CarlaActor);
  void AddVehicleAnimation(FCarlaActor *CarlaActor);
  void AddTrafficLightState(FCarlaActor *CarlaActor);
  void AddVehicleLight(FCarlaActor *CarlaActor);
  void AddActorKinematics(FCarlaActor *CarlaActor);
  void AddActorBoundingBox(FCarlaActor *CarlaActor);
  void AddDReyeVRData();
};
