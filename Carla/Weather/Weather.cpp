// Copyright (c) 2017 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include "Carla.h"
#include "Carla/Weather/Weather.h"
#include "Carla/Game/CarlaStatics.h"

AWeather::AWeather(const FObjectInitializer& ObjectInitializer)
  : Super(ObjectInitializer)
{
  PrimaryActorTick.bCanEverTick = false;
  RootComponent = ObjectInitializer.CreateDefaultSubobject<USceneComponent>(this, TEXT("RootComponent"));
}

void AWeather::ApplyWeather(const FWeatherParameters &InWeather)
{
  SetWeather(InWeather);

#ifdef CARLA_WEATHER_EXTRA_LOG
  UE_LOG(LogCarla, Log, TEXT("Changing weather:"));
  UE_LOG(LogCarla, Log, TEXT("  - Cloudiness = %.2f"), Weather.Cloudiness);
  UE_LOG(LogCarla, Log, TEXT("  - Precipitation = %.2f"), Weather.Precipitation);
  UE_LOG(LogCarla, Log, TEXT("  - PrecipitationDeposits = %.2f"), Weather.PrecipitationDeposits);
  UE_LOG(LogCarla, Log, TEXT("  - WindIntensity = %.2f"), Weather.WindIntensity);
  UE_LOG(LogCarla, Log, TEXT("  - SunAzimuthAngle = %.2f"), Weather.SunAzimuthAngle);
  UE_LOG(LogCarla, Log, TEXT("  - SunAltitudeAngle = %.2f"), Weather.SunAltitudeAngle);
  UE_LOG(LogCarla, Log, TEXT("  - FogDensity = %.2f"), Weather.FogDensity);
  UE_LOG(LogCarla, Log, TEXT("  - FogDistance = %.2f"), Weather.FogDistance);
  UE_LOG(LogCarla, Log, TEXT("  - FogFalloff = %.2f"), Weather.FogFalloff);
  UE_LOG(LogCarla, Log, TEXT("  - Wetness = %.2f"), Weather.Wetness);
  UE_LOG(LogCarla, Log, TEXT("  - ScatteringIntensity = %.2f"), Weather.ScatteringIntensity);
  UE_LOG(LogCarla, Log, TEXT("  - MieScatteringScale = %.2f"), Weather.MieScatteringScale);
  UE_LOG(LogCarla, Log, TEXT("  - RayleighScatteringScale = %.2f"), Weather.RayleighScatteringScale);
#endif // CARLA_WEATHER_EXTRA_LOG

  // Call the blueprint that actually changes the weather.
  RefreshWeather(Weather);
}

void AWeather::NotifyWeather()
{
  // Call the blueprint that actually changes the weather.
  RefreshWeather(Weather);
}

void AWeather::SetWeather(const FWeatherParameters &InWeather)
{
  // check if weather has changed (else, do nothing)
  if (InWeather != Weather)
  {
    Weather = InWeather;

    // Record the weather update
    AddWeatherToRecorder();
  }
}

void AWeather::AddWeatherToRecorder() const
{
  auto *Recorder = UCarlaStatics::GetRecorder(GetWorld());
  if (Recorder && Recorder->IsEnabled())
  {
    Recorder->AddWeather(GetCurrentWeather());
  }
}

AWeather *AWeather::FindWeatherInstance(UWorld *World)
{
  if(World)
  {
    // find the Weather actor in the world (TODO: spawn if necessary)
    TArray<AActor*> FoundWeathers;
    UGameplayStatics::GetAllActorsOfClass(World, AWeather::StaticClass(), FoundWeathers);
    if (FoundWeathers.Num() > 0)
    {
      /// TODO: check for more than one weather(s)
      return CastChecked<AWeather>(FoundWeathers[0]);
    }
    else
    {
      UE_LOG(LogCarla, Error, TEXT("No Weather actor found in world"));
      return nullptr;
    }
  }
  UE_LOG(LogCarla, Error, TEXT("UWorld unavailable for finding weather"));
  return nullptr;
}
