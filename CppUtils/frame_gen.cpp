#include <iostream>
#include <fstream>
#include <random>
#include <cstdint>
using namespace std;

struct IMUFrame
{
    uint8_t header[2];
    uint8_t length;
    uint8_t recognition;
    uint32_t count;
    uint8_t state;
    float pitch;
    float roll;
    float yaw;
    float yaw_gps;
    float pitch_rate;
    float roll_rate;
    float yaw_rate;
    float longtitude;
    float latitude;
    float baro_altitude;
    float gps_altitude;
    float altitude;
    float velocity_north;
    float velocity_east;
    float velocity_down;
    float velocity_air;
    float acceleration_north;
    float acceleration_east;
    float acceleration_down;
    uint8_t satellite_count;
    uint16_t hdop;
    uint16_t vdop;
    uint8_t gps_status;
    uint8_t gps_hh;
    uint8_t gps_mm;
    uint8_t gps_ss;
    uint8_t temperature;
    uint16_t HDT;
    uint16_t HDG_Dev;
};

int main()
{
    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<double> dist(0.0, 1.0);
    double average = 0.0;
    for(int i = 0; i < 100; i++)
    {
        average += dist(gen);
    }
    cout<< average / 100.0 << endl;
}