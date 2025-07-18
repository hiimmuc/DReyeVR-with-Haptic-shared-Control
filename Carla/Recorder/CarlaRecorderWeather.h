// Copyright (c) 2020 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#pragma once

#include <fstream>
#include <vector>
#include "Carla/Weather/WeatherParameters.h"

#pragma pack(push, 1)
struct CarlaRecorderWeather
{

  FWeatherParameters Params;

  void Read(std::ifstream &InFile);

  void Write(std::ofstream &OutFile) const;

  std::string Print() const;
};
#pragma pack(pop)

struct CarlaRecorderWeathers
{
public:

  void Add(const CarlaRecorderWeather &InObj);

  void Clear(void);

  void Write(std::ofstream &OutFile) const;

private:

  std::vector<CarlaRecorderWeather> Weathers;
};
