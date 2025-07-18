// Copyright (c) 2017 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include "CarlaReplayer.h"
#include "CarlaRecorder.h"
#include "Carla/Game/CarlaEpisode.h"

// DReyeVR include
#include "Carla/Actor/DReyeVRCustomActor.h" // ADReyeVRCustomActor::ActiveCustomActors
#include "Carla/Sensor/DReyeVRSensor.h"     // ADReyeVRSensor

#include <ctime>
#include <sstream>

// structure to save replaying info when need to load a new map (static member by now)
CarlaReplayer::PlayAfterLoadMap CarlaReplayer::Autoplay { false, "", "", 0.0, 0.0, 0, 1.0, false };

void CarlaReplayer::Stop(bool bKeepActors)
{
  if (Enabled)
  {
    Enabled = false;

    // destroy actors if event was recorded?
    if (!bKeepActors)
    {
      ProcessToTime(TotalTime, false);
    }

    // callback
    Helper.ProcessReplayerFinish(bKeepActors, IgnoreHero, IsHeroMap);

    // turn off DReyeVR replay
    if (GetEgoSensor())
      GetEgoSensor()->StopReplaying();
  }

  File.close();
}

bool CarlaReplayer::ReadHeader()
{
  if (File.eof())
  {
    return false;
  }

  ReadValue<char>(File, Header.Id);
  ReadValue<uint32_t>(File, Header.Size);

  return true;
}

void CarlaReplayer::SkipPacket(void)
{
  File.seekg(Header.Size, std::ios::cur);
}

void CarlaReplayer::Rewind(void)
{
  CurrentTime = 0.0f;
  TotalTime = 0.0f;
  TimeToStop = 0.0f;

  File.clear();
  File.seekg(0, std::ios::beg);

  // mark as header as invalid to force reload a new one next time
  Frame.Elapsed = -1.0f;
  Frame.DurationThis = 0.0f;

  MappedId.clear();
  IsHeroMap.clear();

  // read geneal Info
  RecInfo.Read(File);
}

// read last frame in File and return the Total time recorded
double CarlaReplayer::GetTotalTime(void)
{
  std::streampos Current = File.tellg();

  // parse only frames
  while (File)
  {
    // get header
    if (!ReadHeader())
    {
      break;
    }

    // check for a frame packet
    switch (Header.Id)
    {
      case static_cast<char>(CarlaRecorderPacketId::FrameStart):
        Frame.Read(File);
        break;
      default:
        SkipPacket();
        break;
    }
  }

  File.clear();
  File.seekg(Current, std::ios::beg);
  return Frame.Elapsed;
}

// Read all the frames and collect their start times
void CarlaReplayer::GetFrameStartTimes()
{
  std::streampos Current = File.tellg();

  while (File)
  {
    if (!ReadHeader())
    {
      break;
    }

    switch (Header.Id)
    {
      case static_cast<char>(CarlaRecorderPacketId::FrameStart):
        Frame.Read(File);
        FrameStartTimes.push_back(Frame.Elapsed); // add this time to the global container
        break;
      default:
        SkipPacket();
        break;
    }
  }

  File.clear();
  File.seekg(Current, std::ios::beg); // return to original position
}

std::string CarlaReplayer::ReplayFile(std::string Filename, double TimeStart, double Duration,
    uint32_t ThisFollowId, bool ReplaySensors)
{
  std::stringstream Info;
  std::string s;

  // Capture params in case we restart from the media controls (use same params)
  LastReplay.Filename = Filename;
  LastReplay.TimeStart = TimeStart;
  LastReplay.Duration = Duration;
  LastReplay.ThisFollowId = ThisFollowId;

  // check to stop if we are replaying another
  if (Enabled)
  {
    Stop();
  }

  // get the final path + filename
  std::string Filename2 = GetRecorderFilename(Filename);

  Info << "Replaying File: " << Filename2 << std::endl;

  // try to open
  File.open(Filename2, std::ios::binary);
  if (!File.is_open())
  {
    Info << "File " << Filename2 << " not found on server\n";
    Stop();
    return Info.str();
  }

  // from start
  Rewind();

  // check to load map if different
  if (Episode->GetMapName() != RecInfo.Mapfile)
  {
    if (!Episode->LoadNewEpisode(RecInfo.Mapfile))
    {
      Info << "Could not load mapfile " << TCHAR_TO_UTF8(*RecInfo.Mapfile) << std::endl;
      Stop();
      return Info.str();
    }
    Info << "Loading map " << TCHAR_TO_UTF8(*RecInfo.Mapfile) << std::endl;
    Info << "Replayer will start after map is loaded..." << std::endl;

    // prepare autoplay after map is loaded
    Autoplay.Enabled = true;
    Autoplay.Filename = Filename2;
    Autoplay.Mapfile = RecInfo.Mapfile;
    Autoplay.TimeStart = TimeStart;
    Autoplay.Duration = Duration;
    Autoplay.FollowId = ThisFollowId;
    Autoplay.TimeFactor = TimeFactor;
    Autoplay.ReplaySensors = ReplaySensors;
  }

  // get Total time of recorder
  TotalTime = GetTotalTime();
  Info << "Total time recorded: " << TotalTime << std::endl;

  // set time to start replayer
  if (TimeStart < 0.0f)
  {
    TimeStart = TotalTime + TimeStart;
    if (TimeStart < 0.0f)
      TimeStart = 0.0f;
  }

  // set time to stop replayer
  if (Duration > 0.0f)
    TimeToStop = TimeStart + Duration;
  else
    TimeToStop = TotalTime;

  Info << "Replaying from " << TimeStart << " s - " << TimeToStop << " s (" << TotalTime << " s) at " <<
      std::setprecision(1) << std::fixed << TimeFactor << "x" << std::endl;

  // set the follow Id
  FollowId = ThisFollowId;

  bReplaySensors = ReplaySensors;
  // if we don't need to load a new map, then start
  if (!Autoplay.Enabled)
  {
    Helper.RemoveStaticProps();
    // process all events until the time
    ProcessToTime(TimeStart, true);
    // mark as enabled
    Enabled = true;
  }

  return Info.str();
}

void CarlaReplayer::CheckPlayAfterMapLoaded(void)
{

  // check if the autoplay is enabled (means waiting until map is loaded)
  if (!Autoplay.Enabled)
    return;

  // disable
  Autoplay.Enabled = false;

  // check to stop if we are replaying another
  if (Enabled)
  {
    Stop();
  }

  // try to open
  File.open(Autoplay.Filename, std::ios::binary);
  if (!File.is_open())
  {
    return;
  }

  // from start
  Rewind();

  // get Total time of recorder
  TotalTime = GetTotalTime();

  // set time to start replayer
  double TimeStart = Autoplay.TimeStart;
  if (TimeStart < 0.0f)
  {
    TimeStart = TotalTime + Autoplay.TimeStart;
    if (TimeStart < 0.0f)
      TimeStart = 0.0f;
  }

  // set time to stop replayer
  if (Autoplay.Duration > 0.0f)
    TimeToStop = TimeStart + Autoplay.Duration;
  else
    TimeToStop = TotalTime;

  // set the follow Id
  FollowId = Autoplay.FollowId;

  bReplaySensors = Autoplay.ReplaySensors;

  // apply time factor
  TimeFactor = Autoplay.TimeFactor;

  Helper.RemoveStaticProps();

  // process all events until the time
  ProcessToTime(TimeStart, true);

  // mark as enabled
  Enabled = true;
}

class ADReyeVRSensor *CarlaReplayer::GetEgoSensor()
{
  if (EgoSensor.IsValid()) {
    return EgoSensor.Get();
  }
  // not tracked yet, lets find the EgoSensor
  if (Episode == nullptr) {
    DReyeVR_LOG_ERROR("No Replayer Episode available!");
    return nullptr;
  }
  EgoSensor = ADReyeVRSensor::GetDReyeVRSensor(Episode->GetWorld());
  if (!EgoSensor.IsValid()) {
    DReyeVR_LOG_ERROR("No EgoSensor available!");
    return nullptr;
  }
  return EgoSensor.Get();
}

template<>
void CarlaReplayer::ProcessDReyeVR<DReyeVR::AggregateData>(double Per, double DeltaTime)
{
  uint16_t Total;
  // read number of DReyeVR entries
  ReadValue<uint16_t>(File, Total); // read number of events
  check(Total == 1); // should be only one Agg data
  for (uint16_t i = 0; i < Total; ++i)
  {
    struct DReyeVRDataRecorder<DReyeVR::AggregateData> Instance;
    Instance.Read(File);
    Helper.ProcessReplayerDReyeVR<DReyeVR::AggregateData>(GetEgoSensor(), Instance.Data, Per);
  }
}

template<>
void CarlaReplayer::ProcessDReyeVR<DReyeVR::ConfigFileData>(double Per, double DeltaTime)
{
  uint16_t Total;
  // read number of DReyeVR entries
  ReadValue<uint16_t>(File, Total); // read number of events
  check(Total == 1); // should be only one ConfigFile data
  for (uint16_t i = 0; i < Total; ++i)
  {
    struct DReyeVRDataRecorder<DReyeVR::ConfigFileData> Instance;
    Instance.Read(File);
    Helper.ProcessReplayerDReyeVR<DReyeVR::ConfigFileData>(GetEgoSensor(), Instance.Data, Per);
  }
}

template<>
void CarlaReplayer::ProcessDReyeVR<DReyeVR::CustomActorData>(double Per, double DeltaTime)
{
  uint16_t Total;
  ReadValue<uint16_t>(File, Total); // read number of events
  CustomActorsVisited.clear();
  for (uint16_t i = 0; i < Total; ++i)
  {
    struct DReyeVRDataRecorder<DReyeVR::CustomActorData> Instance;
    Instance.Read(File);
    Helper.ProcessReplayerDReyeVR<DReyeVR::CustomActorData>(GetEgoSensor(), Instance.Data, Per);
    auto Name = Instance.GetUniqueName();
    CustomActorsVisited.insert(Name); // to track lifetime
  }

  for (auto It = ADReyeVRCustomActor::ActiveCustomActors.begin(); It != ADReyeVRCustomActor::ActiveCustomActors.end();){
    const std::string &ActiveActorName = It->first;
    if (CustomActorsVisited.find(ActiveActorName) == CustomActorsVisited.end()) // currently alive actor who was not visited... time to disable
    {
      // now this has to be garbage collected
      auto Next = std::next(It, 1); // iterator following the last removed element
      It->second->Deactivate();
      It = Next;
    }
    else
    {
      ++It; // increment iterator if not erased
    }
  }
}

void CarlaReplayer::ProcessToTime(double Time, bool IsFirstTime)
{
  double Per = 0.0f;
  double NewTime = CurrentTime + Time;
  bool bFrameFound = false;
  bool bExitAtNextFrame = false;
  bool bExitLoop = false;

  // check if we are in the right frame
  if (NewTime >= Frame.Elapsed && NewTime < Frame.Elapsed + Frame.DurationThis)
  {
    Per = (NewTime - Frame.Elapsed) / Frame.DurationThis;
    bFrameFound = true;
    bExitLoop = true;
  }

  // process all frames until time we want or end
  while (!File.eof() && !bExitLoop)
  {
    // get header
    ReadHeader();

    // check for a frame packet
    switch (Header.Id)
    {
      // frame
      case static_cast<char>(CarlaRecorderPacketId::FrameStart):
        // only read if we are not in the right frame
        Frame.Read(File);
        // check if target time is in this frame
        if (NewTime < Frame.Elapsed + Frame.DurationThis)
        {
          Per = (NewTime - Frame.Elapsed) / Frame.DurationThis;
          bFrameFound = true;
        }
        break;

      // events add
      case static_cast<char>(CarlaRecorderPacketId::EventAdd):
        ProcessEventsAdd();
        break;

      // events del
      case static_cast<char>(CarlaRecorderPacketId::EventDel):
        ProcessEventsDel();
        break;

      // events parent
      case static_cast<char>(CarlaRecorderPacketId::EventParent):
        ProcessEventsParent();
        break;

      // collisions
      case static_cast<char>(CarlaRecorderPacketId::Collision):
        SkipPacket();
        break;

      // positions
      case static_cast<char>(CarlaRecorderPacketId::Position):
        if (bFrameFound)
          ProcessPositions(IsFirstTime);
        else
          SkipPacket();
        break;

      // states
      case static_cast<char>(CarlaRecorderPacketId::State):
        if (bFrameFound)
          ProcessStates();
        else
          SkipPacket();
        break;

      // vehicle animation
      case static_cast<char>(CarlaRecorderPacketId::AnimVehicle):
        if (bFrameFound)
          ProcessAnimVehicle();
        else
          SkipPacket();
        break;

      // walker animation
      case static_cast<char>(CarlaRecorderPacketId::AnimWalker):
        if (bFrameFound)
          ProcessAnimWalker();
        else
          SkipPacket();
        break;

      // vehicle light animation
      case static_cast<char>(CarlaRecorderPacketId::VehicleLight):
        if (bFrameFound)
          ProcessLightVehicle();
        else
          SkipPacket();
        break;

      // scene lights animation
      case static_cast<char>(CarlaRecorderPacketId::SceneLight):
        if (bFrameFound)
          ProcessLightScene();
        else
          SkipPacket();
        break;

      // weather state
      case static_cast<char>(CarlaRecorderPacketId::Weather):
        ProcessWeather();
        break;

      // DReyeVR ego sensor data
      case static_cast<char>(CarlaRecorderPacketId::DReyeVR):
        if (bFrameFound)
          ProcessDReyeVR<DReyeVR::AggregateData>(Per, Time);
        else
          SkipPacket();
        break;

      // DReyeVR custom actor data
      case static_cast<char>(CarlaRecorderPacketId::DReyeVRCustomActor):
        if (bFrameFound)
          ProcessDReyeVR<DReyeVR::CustomActorData>(Per, Time);
        else
          SkipPacket();
        break;
      
      // DReyeVR config file data
      case static_cast<char>(CarlaRecorderPacketId::DReyeVRConfigFile):
        if (bFrameFound)
          ProcessDReyeVR<DReyeVR::ConfigFileData>(Per, Time);
        else
          SkipPacket();
        break;

      // frame end
      case static_cast<char>(CarlaRecorderPacketId::FrameEnd):
        if (bFrameFound)
          bExitLoop = true;
        break;

      // unknown packet, just skip
      default:
        // skip packet
        SkipPacket();
        break;

    }
  }

  // update all positions
  if (Enabled && bFrameFound)
  {
    UpdatePositions(Per, Time);
  }

  // save current time
  CurrentTime = NewTime;

  // stop replay?
  if (CurrentTime >= TimeToStop)
  {
    // keep actors in scene and let them continue with autopilot
    Stop(true);
  }
}

void CarlaReplayer::ProcessEventsAdd(void)
{
  uint16_t i, Total;
  CarlaRecorderEventAdd EventAdd;

  // process creation events
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    EventAdd.Read(File);

    // auto Result = CallbackEventAdd(
    auto Result = Helper.ProcessReplayerEventAdd(
        EventAdd.Location,
        EventAdd.Rotation,
        EventAdd.Description,
        EventAdd.DatabaseId,
        IgnoreHero,
        bReplaySensors);

    switch (Result.first)
    {
      // actor not created
      case 0:
        UE_LOG(LogCarla, Log, TEXT("actor could not be created"));
        break;

      // actor created but with different id
      case 1:
        // mapping id (recorded Id is a new Id in replayer)
        MappedId[EventAdd.DatabaseId] = Result.second;
        break;

      // actor reused from existing
      case 2:
        // mapping id (say desired Id is mapped to what)
        MappedId[EventAdd.DatabaseId] = Result.second;
        break;
    }

    // check to mark if actor is a hero vehicle or not
    if (Result.first > 0)
    {
      // init
      IsHeroMap[Result.second] = false;
      for (const auto &Item : EventAdd.Description.Attributes)
      {
        if (Item.Id == "role_name" && Item.Value == "hero")
        {
          // mark as hero
          IsHeroMap[Result.second] = true;
          break;
        }
      }
    }
  }
}

void CarlaReplayer::ProcessEventsDel(void)
{
  uint16_t i, Total;
  CarlaRecorderEventDel EventDel;

  // process destroy events
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    EventDel.Read(File);
    Helper.ProcessReplayerEventDel(MappedId[EventDel.DatabaseId]);
    MappedId.erase(EventDel.DatabaseId);
  }
}

void CarlaReplayer::ProcessEventsParent(void)
{
  uint16_t i, Total;
  CarlaRecorderEventParent EventParent;
  std::stringstream Info;

  // process parenting events
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    EventParent.Read(File);
    Helper.ProcessReplayerEventParent(MappedId[EventParent.DatabaseId], MappedId[EventParent.DatabaseIdParent]);
  }
}

void CarlaReplayer::ProcessStates(void)
{
  uint16_t i, Total;
  CarlaRecorderStateTrafficLight StateTrafficLight;
  std::stringstream Info;

  // read Total traffic light states
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    StateTrafficLight.Read(File);

    StateTrafficLight.DatabaseId = MappedId[StateTrafficLight.DatabaseId];
    if (!Helper.ProcessReplayerStateTrafficLight(StateTrafficLight))
    {
      UE_LOG(LogCarla,
          Log,
          TEXT("callback state traffic light %d called but didn't work"),
          StateTrafficLight.DatabaseId);
    }
  }
}

void CarlaReplayer::ProcessAnimVehicle(void)
{
  uint16_t i, Total;
  CarlaRecorderAnimVehicle Vehicle;
  std::stringstream Info;

  // read Total Vehicles
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    Vehicle.Read(File);
    Vehicle.DatabaseId = MappedId[Vehicle.DatabaseId];
    // check if ignore this actor
    if (!(IgnoreHero && IsHeroMap[Vehicle.DatabaseId]))
    {
      Helper.ProcessReplayerAnimVehicle(Vehicle);
    }
  }
}

void CarlaReplayer::ProcessAnimWalker(void)
{
  uint16_t i, Total;
  CarlaRecorderAnimWalker Walker;
  std::stringstream Info;

  // read Total walkers
  ReadValue<uint16_t>(File, Total);
  for (i = 0; i < Total; ++i)
  {
    Walker.Read(File);
    Walker.DatabaseId = MappedId[Walker.DatabaseId];
    // check if ignore this actor
    if (!(IgnoreHero && IsHeroMap[Walker.DatabaseId]))
    {
      Helper.ProcessReplayerAnimWalker(Walker);
    }
  }
}

void CarlaReplayer::ProcessLightVehicle(void)
{
  uint16_t Total;
  CarlaRecorderLightVehicle LightVehicle;

  // read Total walkers
  ReadValue<uint16_t>(File, Total);
  for (uint16_t i = 0; i < Total; ++i)
  {
    LightVehicle.Read(File);
    LightVehicle.DatabaseId = MappedId[LightVehicle.DatabaseId];
    // check if ignore this actor
    if (!(IgnoreHero && IsHeroMap[LightVehicle.DatabaseId]))
    {
      Helper.ProcessReplayerLightVehicle(LightVehicle);
    }
  }
}

void CarlaReplayer::ProcessLightScene(void)
{
  uint16_t Total;
  CarlaRecorderLightScene LightScene;

  // read Total light events
  ReadValue<uint16_t>(File, Total);
  for (uint16_t i = 0; i < Total; ++i)
  {
    LightScene.Read(File);
    Helper.ProcessReplayerLightScene(LightScene);
  }
}

void CarlaReplayer::ProcessWeather(void)
{
  uint16_t Total;
  CarlaRecorderWeather Weather;

  // read Total light events
  ReadValue<uint16_t>(File, Total);
  for (uint16_t i = 0; i < Total; ++i)
  {
    Weather.Read(File);
    Helper.ProcessReplayerWeather(Weather);
  }
}

void CarlaReplayer::ProcessPositions(bool IsFirstTime)
{
  uint16_t i, Total;

  // save current as previous
  PrevPos = std::move(CurrPos);

  // read all positions
  ReadValue<uint16_t>(File, Total);
  CurrPos.clear();
  CurrPos.reserve(Total);
  for (i = 0; i < Total; ++i)
  {
    CarlaRecorderPosition Pos;
    Pos.Read(File);
    // assign mapped Id
    auto NewId = MappedId.find(Pos.DatabaseId);
    if (NewId != MappedId.end())
    {
      Pos.DatabaseId = NewId->second;
    }
    else
      UE_LOG(LogCarla, Log, TEXT("Actor not found when trying to move from replayer (id. %d)"), Pos.DatabaseId);
    CurrPos.push_back(std::move(Pos));
  }

  // check to copy positions the first time
  if (IsFirstTime)
  {
    PrevPos.clear();
  }
}

void CarlaReplayer::UpdatePositions(double Per, double DeltaTime)
{
  unsigned int i;
  uint32_t NewFollowId = 0;
  std::unordered_map<int, int> TempMap;

  // map the id of all previous positions to its index
  for (i = 0; i < PrevPos.size(); ++i)
  {
    TempMap[PrevPos[i].DatabaseId] = i;
  }

  // get the Id of the actor to follow
  if (FollowId != 0)
  {
    auto NewId = MappedId.find(FollowId);
    if (NewId != MappedId.end())
    {
      NewFollowId = NewId->second;
    }
  }

  // go through each actor and update
  for (auto &Pos : CurrPos)
  {
    // check if ignore this actor
    if (!(IgnoreHero && IsHeroMap[Pos.DatabaseId]))
    {
      // check if exist a previous position
      auto Result = TempMap.find(Pos.DatabaseId);
      if (Result != TempMap.end())
      {
        // check if time factor is high
        if (TimeFactor >= 2.0)
          // assign first position
          InterpolatePosition(PrevPos[Result->second], Pos, 0.0, DeltaTime);
        else
          // interpolate
          InterpolatePosition(PrevPos[Result->second], Pos, Per, DeltaTime);
      }
      else
      {
        // assign last position (we don't have previous one)
        InterpolatePosition(Pos, Pos, 0.0, DeltaTime);
      }
    }

    // move the camera to follow this actor if required
    if (NewFollowId != 0)
    {
      if (NewFollowId == Pos.DatabaseId)
        Helper.SetCameraPosition(NewFollowId, FVector(-1000, 0, 500), FQuat::MakeFromEuler({0, -25, 0}));
    }
  }
}

// interpolate a position (transform, velocity...)
void CarlaReplayer::InterpolatePosition(
    const CarlaRecorderPosition &Pos1,
    const CarlaRecorderPosition &Pos2,
    double Per,
    double DeltaTime)
{
  // call the callback
  Helper.ProcessReplayerPosition(Pos1, Pos2, Per, DeltaTime);
}

// tick for the replayer
void CarlaReplayer::Tick(float Delta)
{
  TRACE_CPUPROFILER_EVENT_SCOPE(CarlaReplayer::Tick);
  // check if there are events to process (and unpaused)
  if (Enabled && !Paused)
  {
    if (bReplaySync)
    {
      ProcessFrameByFrame();
    }
    else // typical usage (replay as fast as possible with interpolation)
    {
      ProcessToTime(Delta * TimeFactor, false);
    }
  }
}

void CarlaReplayer::ProcessFrameByFrame()
{
  // get the times to process if needed
  if (FrameStartTimes.size() == 0)
  {
    GetFrameStartTimes();
    ensure(FrameStartTimes.size() > 0);
  }

  // process to those times
  ensure(SyncCurrentFrameId < FrameStartTimes.size());
  double LastTime = 0.f;
  if (SyncCurrentFrameId > 0)
    LastTime = FrameStartTimes[SyncCurrentFrameId - 1];
  ProcessToTime(FrameStartTimes[SyncCurrentFrameId] - LastTime, (SyncCurrentFrameId == 0));
  if (GetEgoSensor()) // take screenshot of this frame
    GetEgoSensor()->TakeScreenshot();
  // progress to the next frame
  if (SyncCurrentFrameId < FrameStartTimes.size() - 1)
    SyncCurrentFrameId++;
  else
    Stop();
}

void CarlaReplayer::Restart() 
{
  // Use same params as they were initially
  ReplayFile(LastReplay.Filename, LastReplay.TimeStart,
             LastReplay.Duration, LastReplay.ThisFollowId);
}

void CarlaReplayer::Advance(const float Amnt)
{
  // check out of bounds
  const double DesiredTime = CurrentTime + Amnt;
  if (DesiredTime < 0 || DesiredTime > TotalTime || DesiredTime > TimeToStop)
  {
    return;
  }

  // ignore if 0
  if (Amnt == 0)
  {
    return;
  }
  // forward in time (easy)
  else if (Amnt > 0) 
  {
    /// TODO: verify that this correctly places all actors
    // else can use the Restart+ProcessToTime hack similar to backwards
    ProcessToTime(Amnt, false);
  }
  // backwards in time (harder)
  else
  {
    // // amnt is unit of time (timestep) for replay
    // UE_LOG(LogTemp, Log, TEXT("Want to go back to: %.4f from"), DesiredTime, CurrentTime);
    // int NumAmnts = ((CurrentTime - Frame.Elapsed) / (-Amnt)) + 1;
    // // duration is unit of time (timestep) for recordings
    // int NumDurations = (NumAmnts * (-Amnt)) / Frame.DurationThis;
    // UE_LOG(LogTemp, Log, TEXT("With a duration of %.4f, this'll take %d prevs"), Frame.DurationThis, NumDurations);
    // for (size_t i = 0; i < NumDurations; i++)
    // {
    //   PrevPacket(); // go backwards in the file
    // }
    // UE_LOG(LogTemp, Log, TEXT("Now the time is: %.3f"), Frame.Elapsed);
    // // back to negative
    // ProcessToTime(Amnt, false);
    Stop(true); // stops the replaying while keeping actors (dosen't destroy & respawn)
    Restart();
    ProcessToTime(DesiredTime, true);
  }
}