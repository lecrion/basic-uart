json: ./bin/libjson.a

./bin/libjson.a: ./build/json.o
	ar rcs $@ $^

./build/json.o: ./src/json.cpp ./include/json.hpp
	g++ -c $< -o $@ -I./include
