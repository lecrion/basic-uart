#include <iostream>
#include <string>
#include <cstring>
#include <cstdint>
using namespace std;

typedef float fp32;
typedef double fp64;

inline uint8_t to_uint8(char str[])
{
    if(str[0] >= 'a' && str[0] <= 'f') str[0] += 'A' - 'a';
    if(str[1] >= 'a' && str[1] <= 'f') str[1] += 'A' - 'a';
    uint8_t ans = 0;
    if(str[0] >= '0' && str[0] <= '9') ans = str[0] - '0';
    else ans = str[0] - 'A' + 10;
    ans *= 16;
    if(str[1] >= '0' && str[1] <= '9') ans += str[1] - '0';
    else ans += str[1] - 'A' + 10;
    return ans;
}

int main(int argc, char * argv[])
{
    if(argc < 2)
    return 0;
    string decoder(argv[1]);
    uint8_t uint8_ans = 0;
    int8_t int8_ans = 0;
    uint16_t uint16_ans = 0;
    int16_t int16_ans = 0;
    uint32_t uint32_ans = 0;
    int32_t int32_ans = 0;
    fp32 fp32_ans = 0.0f;
    fp64 fp64_ans = 0.0;
    uint8_t data[8] = {0};

    for(int i = 2, j = 0; i < argc; i++, j++)
    data[j] = to_uint8(argv[i]);
    
    if(decoder == "uint8")
    {
        memcpy(&uint8_ans, data, 1);
        cout << (uint32_t)uint8_ans << endl;
    }
    else if(decoder == "int8")
    {
        memcpy(&int8_ans, data, 1);
        cout << (uint32_t)int8_ans << endl;
    }
    else if(decoder == "uint16")
    {
        memcpy(&uint16_ans, data, 2);
        cout << uint16_ans << endl;
    }
    else if(decoder == "int16")
    {
        memcpy(&int16_ans, data, 2);
        cout << int16_ans << endl;
    }
    else if(decoder == "uint32")
    {
        memcpy(&uint32_ans, data, 4);
        cout << uint32_ans << endl;
    }
    else if(decoder == "int32")
    {
        memcpy(&int32_ans, data, 4);
        cout << int32_ans << endl;
    }
    else if(decoder == "fp32")
    {
        memcpy(&fp32_ans, data, 4);
        cout << fp32_ans << endl;
    }
    else if(decoder == "fp64")
    {
        memcpy(&fp64_ans, data, 8);
        cout << fp64_ans << endl;
    }
    return 0;
}