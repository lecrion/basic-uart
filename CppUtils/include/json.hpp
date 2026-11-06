#ifndef JSON_HPP
#define JSON_HPP

#include <fstream>
#include <sstream>
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <set>
#include <cctype>
#include <utility>

class JsonObject
{
private:
    enum class Type
    {
        OBJECT,
        ARRAY,
        NUMBER_DOUBLE,
        NUMBER_INT,
        STRING,
        BOOLEAN,
        NULLTYPE
    } type;
    std::map<std::string, JsonObject> object_value;
    std::vector<JsonObject> array_value;
    double number_value_double;
    long long number_value_int;
    std::string string_value;
    bool boolean_value;
public:
    /*constructors and destructors*/
    void reset();
    JsonObject():
        type(Type::NULLTYPE) {}
    JsonObject(const JsonObject& other):
        type(other.type),
        object_value(other.object_value),
        array_value(other.array_value),
        number_value_double(other.number_value_double),
        number_value_int(other.number_value_int),
        string_value(other.string_value),
        boolean_value(other.boolean_value) {}
    JsonObject(JsonObject&& other):
        type(other.type),
        object_value(std::move(other.object_value)),
        array_value(std::move(other.array_value)),
        number_value_double(other.number_value_double),
        number_value_int(other.number_value_int),
        string_value(std::move(other.string_value)),
        boolean_value(other.boolean_value) {} 
    JsonObject(std::map<std::string, JsonObject> obj):
        type(Type::OBJECT),
        object_value(std::move(obj)) {}
    JsonObject(std::vector<JsonObject> arr):
        type(Type::ARRAY),
        array_value(std::move(arr)) {}
    JsonObject(double num):
        type(Type::NUMBER_DOUBLE),
        number_value_double(num) {}
    JsonObject(long long num):
        type(Type::NUMBER_INT),
        number_value_int(num) {}
    JsonObject(std::string str):
        type(Type::STRING),
        string_value(std::move(str)) {}
    JsonObject(const char str[]):
        type(Type::STRING),
        string_value(str) {}
    JsonObject(const bool boolean):
        type(Type::BOOLEAN),
        boolean_value(boolean) {}
    JsonObject(const std::nullptr_t):
        type(Type::NULLTYPE) {}
    ~JsonObject() {}

    /*convert between char string and JsonObject*/
    std::string to_string() const;
    static JsonObject parse(const char str[], int& ptr);
    static JsonObject parse(const char str[]);
    static JsonObject parse(const std::string& str);
    static JsonObject parse(std::istream& input);

    /*get type*/
    bool is_object() const { return type == Type::OBJECT; };
    bool is_array() const { return type == Type::ARRAY; };
    bool is_number() const { return type == Type::NUMBER_DOUBLE || type == Type::NUMBER_INT; };
    bool is_int() const { return type == Type::NUMBER_INT; };
    bool is_double() const { return type == Type::NUMBER_DOUBLE; };
    bool is_string() const { return type == Type::STRING; };
    bool is_boolean() const { return type == Type::BOOLEAN; };
    bool is_null() const { return type == Type::NULLTYPE; };

    /*set type*/
    void set_as_object() { type = Type::OBJECT; object_value.clear(); };
    void set_as_array() { type = Type::ARRAY; array_value.clear(); };
    void set_as_number_double() { type = Type::NUMBER_DOUBLE; number_value_double = 0.0; };
    void set_as_number_int() { type = Type::NUMBER_INT; number_value_int = 0; };
    void set_as_string() { type = Type::STRING; string_value.clear(); };
    void set_as_boolean() { type = Type::BOOLEAN; boolean_value = false; };
    void set_as_null() { type = Type::NULLTYPE; };

    /*get sub-objects*/
    JsonObject& operator[](const std::string& key);
    JsonObject& operator[](const int index);

    /*equals*/
    bool operator==(const JsonObject& other) const;
    bool operator!=(const JsonObject& other) const;

    /*assignments*/
    JsonObject& operator=(const JsonObject& other);
    JsonObject& operator=(JsonObject&& other) noexcept;
    JsonObject& operator=(std::map<std::string, JsonObject> obj);
    JsonObject& operator=(std::vector<JsonObject> arr);
    JsonObject& operator=(long long num);
    JsonObject& operator=(double num);
    JsonObject& operator=(std::string str);
    JsonObject& operator=(const char str[]);
    JsonObject& operator=(const bool boolean);
    JsonObject& operator=(const std::nullptr_t);

    /*add to objects and arrays*/
    JsonObject& operator+=(const std::map<std::string, JsonObject>& other);
    JsonObject& operator+=(const std::pair<std::string, JsonObject>& other);
    JsonObject& operator+=(const std::vector<JsonObject>& other);
    JsonObject& operator+=(const JsonObject& other);

    /*remove from objects and arrays*/
    JsonObject& operator-=(const std::map<std::string, JsonObject>& other);
    JsonObject& operator-=(const std::pair<std::string, JsonObject>& other);
    JsonObject& operator-=(const std::vector<JsonObject>& other);
    JsonObject& operator-=(const JsonObject& other);

    /*stream operators*/
    friend std::istream& operator>>(std::istream& in, JsonObject& obj);
    friend std::ostream& operator<<(std::ostream& out, const JsonObject& obj);
};

#endif /* JSON_HPP */