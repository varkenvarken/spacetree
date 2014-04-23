#include <vector>
#include <array>

using namespace std;

typedef array<double, 3> point;
typedef vector<point> points;
typedef vector<int> indices;

int iterate(
	points endpoints,
	points startpoints,
	points additionalendpoints,
	int niterations,
	double branchlength,
	double killdistance,
	double tropism,

	points &branchpoints,
	indices &branchpointparents);

