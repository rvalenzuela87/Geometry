import math
import Vector_Utils as vu
reload(vu)


def triangle_barycentric_coord(point, triangle):
    """
    Calculates the barycentric coordinates for the point passed as first argument in relation to the triangle (list
    containing 3 points) passed as second argument. All points are assumed to be barycentric independent and in R2,
    i.e. 2 dimensional.

        :param point: List or tuple of two numbers
        :param triangle: List containing 3 points (list or tuple)

        :return: List of floats
    """

    # ... Use the point\'s projection to calculate the barycentric coordinates

    area1 = vu.outter_prod_2D(vu.vector_sub(triangle[0], point), vu.vector_sub(triangle[1], point)) * 0.5
    area2 = vu.outter_prod_2D(vu.vector_sub(triangle[1], point), vu.vector_sub(triangle[2], point)) * 0.5
    area3 = vu.outter_prod_2D(vu.vector_sub(triangle[2], point), vu.vector_sub(triangle[0], point)) * 0.5

    '''print("Area 1: {}".format(area1))
    print("Area 2: {}".format(area2))
    print("Area 3: {}".format(area3))'''

    area_t = area1 + area2 + area3

    coord = (area2/area_t, area3/area_t, area1/area_t)

    # print(coord[0] + coord[1] + coord[2])

    return coord


def poly_wachspress_coord(point, polygon):
    """
    Calculates the wachspress coordinates for the point passed as first argument in relation to the convex polygon
    (list of points) passed as second argument. All the points are assumed to be barycentric independent and in R2,
    i.e. 2 dimensional.

        :param point: List or tuple of two numbers
        :param polygon: List containing, at least, 3 points (list or tuple)

        :return: List of float values; one for each of the polygon\'s points
    """

    inner_triangles_areas = [0.0 for __ in range(len(polygon))]     # Polygon's inner triangles' areas
    point_vertex_areas = [0.0 for __ in range(len(polygon))]        # Point-Vertex areas
    weights = [0.0 for __ in range(len(polygon))]    # Weights
    lambdas = [0.0 for __ in range(len(polygon))]    # Lambdas

    weights_sum = 0.0

    for i in range(len( polygon)):
        vertex       = polygon[i]         # Point (tuple or list)
        prev_vertex  = polygon[i - 1]     # Point (tuple or list)

        try:
            next_vertex = polygon[i + 1]  # Point (tuple or list)
        except IndexError:
            next_vertex = polygon[0]

        inner_triangles_areas[i] = vu.outter_prod_2D(
            vu.vector_sub(vertex, prev_vertex),
            vu.vector_sub(next_vertex, vertex)
        )
        point_vertex_areas[i] = vu.outter_prod_2D(
            vu.vector_sub(vertex, point),
            vu.vector_sub(next_vertex, point)
        )

    for i in range(len(polygon)):
        areas_prod = 1.0
        prev_i = i - 1

        if i == 0:
            prev_i = len(polygon) - 1

        for j in range(len(point_vertex_areas)):
            if j in [i, prev_i]:
                continue
            else:
                areas_prod *= point_vertex_areas[j]

        weights[i] = inner_triangles_areas[i] * areas_prod
        weights_sum += weights[i]

    for i in range(len(weights)):
        lambdas[i] = weights[i] / weights_sum

    return lambdas


def poly_mean_value_coord(point, polygon):
    """
    Calculates the mean value coordinates for the point passed as first argument in relation to the polygon (list of
    points) passed as second argument indistinct of it being convex or non-convex. All the points are assumed to be
    barycentric independent and in R2, i.e. 2 dimensional.

        :param point: List or tuple of two numbers
        :param polygon: List containing, at least, 3 points (list or tuple)

        :return: List of float values; one for each of the polygon\'s points
    """

    weights = [0.0 for __ in range(len(polygon))]  # Weights
    lambdas = [0.0 for __ in range(len(polygon))]  # Lambdas

    weights_sum = 0.0

    for i in range(len(polygon)):
        vtx = polygon[i]
        prev_vtx = polygon[i - 1]

        try:
            next_vtx = polygon[i + 1]
        except IndexError:
            next_vtx = polygon[0]

        vtx_min_point = vu.vector_sub(vtx, point)

        angle = vu.angle_between(vtx_min_point, vu.vector_sub(next_vtx, point), True)
        prev_angle = vu.angle_between(vu.vector_sub(prev_vtx, point), vtx_min_point, True)

        weights[i] = (math.tan(prev_angle * 0.5) + math.tan(angle * 0.5)) / math.sqrt(vu.inner_prod(vtx_min_point, vtx_min_point))
        weights_sum += weights[i]

    for i in range(len(weights)):
        lambdas[i] = weights[i] / weights_sum

    return lambdas


def poly_mean_value_coord(point, polygon):
    """
    Calculates the mean value coordinates for the point passed as first argument in relation to the polygon (list of
    points) passed as second argument indistinct of it being convex or non-convex. All the points are assumed to be
    barycentric independent and in R2, i.e. 2 dimensional.

        :param point: List or tuple of two numbers
        :param polygon: List containing, at least, 3 points (list or tuple)

        :return: List of float values; one for each of the polygon\'s points
    """

    weights = [0.0 for __ in range(len(polygon))]  # Weights
    lambdas = [0.0 for __ in range(len(polygon))]  # Lambdas

    weights_sum = 0.0

    for i in range(len(polygon)):
        vtx = polygon[i]
        prev_vtx = polygon[i - 1]

        try:
            next_vtx = polygon[i + 1]
        except IndexError:
            next_vtx = polygon[0]

        point_minus_vertex = vu.vector_sub(vtx, point)

        sigma_angle = vu.angle_between(point_minus_vertex, vu.vector_sub(next_vtx, vtx), True)
        gamma_angle = vu.angle_between(vu.vector_sub(prev_vtx, vtx), point_minus_vertex, True)

        weights[i] = ((1.0/math.tan(gamma_angle)) + (1.0/math.tan(sigma_angle))) / vu.inner_prod(point_minus_vertex, point_minus_vertex)
        weights_sum += weights[i]

    for i in range(len(weights)):
        lambdas[i] = weights[i] / weights_sum

    return lambdas


def generalized_barycentric_coordinates(point, polygon):
    for i in range(len(polygon)):
        vertex = polygon[i]
        next_vertex = polygon[i + 1]
        prev_vertex = polygon[i -1]


def tetrahedron_barycentric_coord(point, tetrahedron):
    lambdas  = [0.0 for __ in tetrahedron]      # Lambdas
    volumes = [0.0 for __ in tetrahedron]      # Volumes

    volumes_sum = 0.0

    for i in range(len(tetrahedron)):
        vtx = tetrahedron[i]

        try:
            next_vtx = tetrahedron[i + 1]
        except IndexError:
            next_vtx = tetrahedron[0]

        try:
            next_next_vtx = tetrahedron[i + 2]
        except IndexError:
            if i > 2:
                next_next_vtx = tetrahedron[1]
            else:
                next_next_vtx = tetrahedron[0]

        vector_a = vu.vector_sub(vtx, point)
        vector_b = vu.vector_sub(next_vtx, point)
        vector_c = vu.vector_sub(next_next_vtx, point)
        
        # print( vu.outter_prod_3D(vector_a, vector_b, vector_c))

        volumes[i - 1] = vu.outter_prod_3D(vector_a, vector_b, vector_c) * (1.0/math.factorial(3))
        volumes_sum += volumes[i - 1]

    # print("Volume total: %f" % vol_t)

    for i in range(len(volumes)):
        lambdas[i] = volumes[i]/volumes_sum

    return lambdas
