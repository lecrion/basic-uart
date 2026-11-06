#include "json.hpp"
#include <algorithm>
#include <stack>

void JsonObject::reset()
{
    type = Type::NULLTYPE;
    object_value.clear();
    array_value.clear();
    number_value_double = 0.0;
    number_value_int = 0;
    string_value.clear();
    boolean_value = false;
}

JsonObject& JsonObject::operator[](const std::string& key)
{
    return object_value[key];
}

JsonObject& JsonObject::operator[](const int index)
{
    return array_value[index];
}

bool JsonObject::operator==(const JsonObject& other) const
{
    if(type != other.type) return false;
    switch(type)
    {
        case Type::OBJECT:
            return object_value == other.object_value;
        case Type::ARRAY:
            return array_value == other.array_value;
        case Type::NUMBER_DOUBLE:
            return number_value_double == other.number_value_double;
        case Type::NUMBER_INT:
            return number_value_int == other.number_value_int;
        case Type::STRING:
            return string_value == other.string_value;
        case Type::BOOLEAN:
            return boolean_value == other.boolean_value;
        case Type::NULLTYPE:
            return true;
    }
    return false;
}

bool JsonObject::operator!=(const JsonObject& other) const
{
    return !(*this == other);
}

JsonObject& JsonObject::operator=(const JsonObject& other)
{
    
    type = other.type;
    object_value = other.object_value;
    array_value = other.array_value;
    number_value_double = other.number_value_double;
    number_value_int = other.number_value_int;
    string_value = other.string_value;
    boolean_value = other.boolean_value;
    return *this;
}

JsonObject& JsonObject::operator=(JsonObject&& other) noexcept
{
    type = other.type;
    object_value = std::move(other.object_value);
    array_value = std::move(other.array_value);
    number_value_double = other.number_value_double;
    number_value_int = other.number_value_int;
    string_value = std::move(other.string_value);
    boolean_value = other.boolean_value;
    return *this;
}

JsonObject& JsonObject::operator=(std::map<std::string, JsonObject> obj)
{
    type = Type::OBJECT;
    object_value = obj;
    return *this;
}

JsonObject& JsonObject::operator=(std::vector<JsonObject> arr)
{
    type = Type::ARRAY;
    array_value = arr;
    return *this;
}

JsonObject& JsonObject::operator=(double num)
{
    type = Type::NUMBER_DOUBLE;
    number_value_double = num;
    return *this;
}

JsonObject& JsonObject::operator=(long long num)
{
    type = Type::NUMBER_INT;
    number_value_int = num;
    return *this;
}

JsonObject& JsonObject::operator=(std::string str)
{
    type = Type::STRING;
    string_value = str;
    return *this;
}

JsonObject& JsonObject::operator=(const char str[])
{
    type = Type::STRING;
    string_value = str;
    return *this;
}

JsonObject& JsonObject::operator=(const bool boolean)
{
    type = Type::BOOLEAN;
    boolean_value = boolean;
    return *this;
}

JsonObject& JsonObject::operator=(const std::nullptr_t)
{
    type = Type::NULLTYPE;
    return *this;
}

JsonObject& JsonObject::operator+=(const std::map<std::string, JsonObject>& other)
{
    if(is_object())
    {
        object_value.insert(other.begin(), other.end());
    }
    return *this;
}

JsonObject& JsonObject::operator+=(const std::pair<std::string, JsonObject>& other)
{
    if(is_object())
    {
        object_value.insert(other);
    }
    return *this;
}

JsonObject& JsonObject::operator+=(const std::vector<JsonObject>& other)
{
    if(is_array())
    {
        array_value.insert(array_value.end(), other.begin(), other.end());
    }
    return *this;
}

JsonObject& JsonObject::operator+=(const JsonObject& other)
{
    if(is_array())
    {
        array_value.push_back(other);
    }
    return *this;
}

JsonObject& JsonObject::operator-=(const std::map<std::string, JsonObject>& other)
{
    if(is_object())
    {
        for(auto i : other)
        {
            object_value.erase(i.first);
        }
    }
    return *this;
}

JsonObject& JsonObject::operator-=(const std::pair<std::string, JsonObject>& other)
{
    if(is_object())
    {
        object_value.erase(other.first);
    }
    return *this;
}

JsonObject& JsonObject::operator-=(const std::vector<JsonObject>& other)
{
    if(is_array())
    {
        for(JsonObject i : other)
        {
            auto pos = std::find(array_value.begin(), array_value.end(), i);
            if(pos != array_value.end())
            {
                array_value.erase(pos);
            }
        }
    }
    return *this;
}

JsonObject& JsonObject::operator-=(const JsonObject& other)
{
    if(is_array())
    {
        auto pos = std::find(array_value.begin(), array_value.end(), other);
        if(pos != array_value.end())
        {
            array_value.erase(pos);
        }
    }
    return *this;
}

std::istream& operator>>(std::istream& in, JsonObject& obj)
{
    std::string result;
    char lbracket, rbracket;
    in >> std::ws;
    char json_start = in.peek();
    if(json_start == '{' || json_start == '[')
    {
        in.get();
        if(json_start == '{')
        {
            lbracket = '{';
            rbracket = '}';
        }
        if(json_start == '[')
        {
            lbracket = '[';
            rbracket = ']';
        }
        std::string buf, tmp;
        buf += lbracket;
        int lbracket_cnt = 1, rbracket_cnt = 0, is_inside_string = 0;
        while(lbracket_cnt > rbracket_cnt)
        {
            std::getline(in, tmp, rbracket);
            buf += (tmp += rbracket);
            for(char ch: tmp)
            {
                if(ch == '"') is_inside_string = !is_inside_string;
                if(ch == lbracket && !is_inside_string) lbracket_cnt++;
            }
            if(!is_inside_string) rbracket_cnt++;
        }
        obj = JsonObject::parse(buf.c_str());
        return in;
    }
    else if(json_start == '"') // one single string
    {
        in.get();
        std::string tmp;
        std::getline(in, tmp, '"');
        obj = tmp;
        return in;
    }
    else if(json_start == 't' || json_start == 'f' || json_start == 'n') // one single boolean / null
    {
        if(json_start == 't')
        {
            obj = true;
            in.ignore(4);
        }
        else if(json_start == 'f')
        {
            obj = false;
            in.ignore(5);
        }
        else if(json_start == 'n')
        {
            obj = nullptr;
            in.ignore(4);
        }
        return in;
    }
    else // one single number
    {
        std::string tmp;
        char ch;
        int is_int = 1;
        while(1)
        {
            ch = in.peek();
            if((ch >= '0' && ch <= '9') || ch == '.' || ch == '-' || ch == '+')
            {
                if(ch == '.') is_int = 0;
                in.get();
                tmp += ch;
            }
            else break;
        }
        if(is_int)
        obj = std::stoll(tmp);
        else
        obj = std::stod(tmp);
        return in;
    }
    
}

std::ostream& operator<<(std::ostream& out, const JsonObject& obj)
{
    out << obj.to_string();
    return out;
}

std::string JsonObject::to_string() const
{
    switch(type)
    {
        case Type::OBJECT:
        {
            std::string result("{");
            for(auto it = object_value.begin(); it != object_value.end(); it++)
            {
                result += "\"" + it->first + "\"" + ": " + it->second.to_string() + ", ";
            }
            result.pop_back();
            result.pop_back();
            result += "}";
            return result;
        }
        case Type::ARRAY:
        {
            std::string result("[");
            for(auto it = array_value.begin(); it != array_value.end(); it++)
            {
                result += it->to_string() + ", ";
            }
            result.pop_back();
            result.pop_back();
            result += "]";
            return result;
        }
        case Type::NUMBER_DOUBLE:
        {
            return std::to_string(number_value_double);
        }
        case Type::NUMBER_INT:
        {
            return std::to_string(number_value_int);
        }
        case Type::STRING:
        {
            return "\"" + string_value + "\""; 
        }
        case Type::BOOLEAN:
        {
            return boolean_value ? "true" : "false";
        }
        case Type::NULLTYPE:
        {
            return "null";
        }
    }
    return "";
}

JsonObject JsonObject::parse(const char str[], int& ptr)
{
    JsonObject result;
    while(std::isspace(str[ptr])) ptr++;
    if(str[ptr] == '{')
    {
        result.type = Type::OBJECT;
        result.object_value.clear();
        ptr++;
        while(str[ptr] != '}')
        {
            int key_start = 0, key_end = 0;
            while(str[ptr] != '"') ptr++;
            key_start = ++ptr;
            while(str[ptr] != '"') ptr++;
            key_end = ptr;
            std::string key(str + key_start, str + key_end);
            while(str[ptr] != ':') ptr++;
            result.object_value[key] = parse(str, ++ptr);
            while(str[ptr] != ',' && str[ptr] != '}') ptr++;
            if(str[ptr] == ',') ptr++;
        }
        ptr++;
        return result;
    }
    else if(str[ptr] == '[')
    {
        result.type = Type::ARRAY;
        result.array_value.clear();
        ptr++;
        while(str[ptr] != ']')
        {
            result.array_value.push_back(parse(str, ptr));
            while(str[ptr] != ',' && str[ptr] != ']') ptr++;
            if(str[ptr] == ',') ptr++;
        }
        ptr++;
        return result;
    }
    else if(str[ptr] == '"')
    {
        result.type = Type::STRING;
        int start = ++ptr;
        while(str[ptr] != '"') ptr++;
        int end = ptr;
        result.string_value.assign(str + start, str + end);
        ptr++;
        return result;
    }
    else if(str[ptr] == 't')
    {
        ptr += 4;
        result.type = Type::BOOLEAN;
        result.boolean_value = true;
        return result;
    }
    else if(str[ptr] == 'f')
    {
        ptr += 5;
        result.type = Type::BOOLEAN;
        result.boolean_value = false;
        return result;
    }
    else if(str[ptr] == 'n')
    {
        ptr += 4;
        result.type = Type::NULLTYPE;
        return result;
    }
    else
    {
        int start = ptr;
        while((str[ptr] >= '0' && str[ptr] <= '9') || str[ptr] == '.' || str[ptr] == '-' || str[ptr] == '+') ptr++;
        int end = ptr;
        std::string number_str(str + start, str + end);
        if(number_str.find('.') != std::string::npos)
        {
            result.type = Type::NUMBER_DOUBLE;
            result.number_value_double = std::stod(number_str);
        }
        else
        {
            result.type = Type::NUMBER_INT;
            result.number_value_int = std::stoll(number_str);
        }
        return result;
    }
}

JsonObject JsonObject::parse(const char str[])
{
    int ptr = 0;
    return parse(str, ptr);
}

JsonObject JsonObject::parse(const std::string& str)
{
    return parse(str.c_str());
}

JsonObject JsonObject::parse(std::istream& input)
{
    std::string str(
        (std::istreambuf_iterator<char>(input)),
        std::istreambuf_iterator<char>()
    );
    return parse(str);
}