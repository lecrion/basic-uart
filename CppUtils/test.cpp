#include "json.hpp"
#include <iostream>
#include <fstream>
using namespace std;

int main()
{
    ifstream file("test.json");
    if(!file.is_open())
    {
        cerr << "file not opened " << endl;
        return 0;
    }
    JsonObject test;
    file >> test;
    file.close();
    cout << test.to_string() << endl << endl;
    return 0;
}