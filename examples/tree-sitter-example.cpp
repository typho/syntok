#include <iostream>

int main() {
	std::cout << "hello " << ([](void){ return "world!"; })() << std::endl;
	return 0;
}
