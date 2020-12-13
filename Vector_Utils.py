import math


def length( vector ):
	"""
	Calculates the vector\'s length  using the theorem of pythagoras and returns it.

		:param vector: List

		:raise: Exception
		:return: Float
	"""

	accum = 0.0

	for c in vector:
		accum += math.pow( c, 2 )

	return math.sqrt( accum )


def vector_arithmetic( vectors, add ):
	"""
	Adds or substracts the vectors passed as arguments depending on the value for the add parameter.

		:param vectors: List of lists or list of tuples
		:param add: Boolean. If true, the function returns the vectors addition, otherwise it
					returns the vectors substraction

		:raise: Exception, IndexError
		:return: List
	"""

	dimension = 0.0

	try:
		dimension = len( vectors[0] )

	except IndexError:
		raise Exception("No vectors received as arguments")

	vector = []

	try:
		for i in range( dimension ):
			accum = 0.0

			for j in range( len( vectors ) ):
				if add:
					accum += vectors[j][i]

				else:
					if j > 0:
						accum -= vectors[j][i]
					else:
						accum = vectors[j][i]

			vector.append(accum)

	except IndexError:
		raise Exception( "Vectors passed as argument have different dimensions" )

	return vector


def vector_add( *args ):
	vectors = None

	if len( args ) == 0:
		''' Assume args[0] is a list of vectors'''
		try:
			vectors = args[0]
		except IndexError:
			raise Exception(
				"This function expects a list of vectors (lists or tuples) when a single argument is used "
				"at calling time. Otherwise it expects N arguments, each of them a vector (list or "
				"tuple. Exiting...)"
			)
	else:
		vectors = [ v for v in args ]

	return vector_arithmetic( vectors, True )


def vector_sub( *args ):
	"""
	Receives a single list of vectors (lists or tuples) or an N number of vectors as arguments.

		:param *: When a single argument is passed at calling time, the function expects a list of vectors (lists or
				tuples); when multiple arguments are passed the function expects each of them to be vector (list or
				tuple) all elements of the same vector space.

		:raise: Exception, IndexError
		:return: List
	"""

	vectors = None

	if len( args ) == 0:
		''' Assume args[0] is a list of vectors'''
		try:
			vectors = args[0]
		except IndexError:
			raise Exception(
				"This function expects a list of vectors (lists or tuples) when a single argument is used "
				"at calling time. Otherwise it expects N arguments, each of them a vector (list or "
				"tuple. Exiting...)"
			)
	else:
		vectors = [ v for v in args ]

	return vector_arithmetic( vectors, False )


def vector_scalar_prod( vector, scalar ):
	"""
	Scales the vector by the value passed as argument for the scalar parameter and returns it.

		:param vector: List or tuple
		:param scalar: Integer, float or double

		:raise: Exception
		:return: List
	"""

	try:
		return [ scalar * c for c in vector ]

	except Exception:
		raise


def vector_basis_prod( vector, basis ):
	"""
	Transforms a vector with a set of basis vectors and returns it.

		:param vector: List
		:param basis: List of lists or list of tuples

		:raise: Exception
		:return: List
	"""

	scaled_basis = []

	try:
		scaled_basis = [ vector_scalar_prod( vector[i], basis[i] ) for i in range( len( vector ) ) ]

	except IndexError as exc:
		mssg = "Not enough basis vectors provided. Expected %i, got %i instead. Exiting..." % (len(vector), len(basis))
		raise Exception( mssg )

	else:
		result = None

		for i in range( len( scaled_basis ) ):
			if i == 0:
				result = scaled_basis[i]
			else:
				result = vector_add( result, scaled_basis[i] )

		return result


def angle_between( vector_a, vector_b, rad = False ):
	"""
	Calculates the angle between two vectors using the cosine universal formula

		:param vector_a: List or tuple
		:param vector_b: List or tuple
		:param rad: Boolean. False as default

		:return: Angle or radians depending on the value of rad parameter.
	"""

	vector_a_len = length( vector_a )
	vector_b_len = length( vector_b )

	cos_angle = ( math.pow( vector_a_len, 2 ) + math.pow( vector_b_len, 2 ) - math.pow( length( vector_sub( vector_a, vector_b ) ),2 ) ) / ( 2 * vector_a_len * vector_b_len )

	if rad is False:
		return math.degrees( math.acos( cos_angle ) ) 	# Degrees
	else:
		return math.acos( cos_angle ) 	# Radians


def inner_prod( vector_a, vector_b ):
	"""
	This function assumes vector_a and vector_b have orthonormal basis and returns their inner product.

		:param vector_a: List
		:param vector_b: List

		:raise: Exception
		:return: Float
	"""

	inn_prod = 0.0

	try:
		for prod in [ vector_a[i] * vector_b[i] for i in range( len( vector_a ) ) ]:
			inn_prod += prod

	except IndexError:
		raise Exception( "Vectors have different dimensions: %i /= %i" % ( len( vector_a ), len( vector_b ) ) )

	else:
		return inn_prod


def inner_prod_grl( vector_a, vector_b, basis_a = None, basis_b = None ):
	"""
	Calculates the inner product of two vectors( vector_a and vector_b ) taking into account each vector\'s basis.

		:param vector_a: List
		:param vector_b: List
		:param basis_a: List of lists or list of tuples; one list or tuple per element of vector_a
		:param basis_b: List of lists or list of tuples; one list or tuple per element of vector_b

		:raise: Exception, IndexError
		:return: Float
	"""

	try:
		vector_a_a = vector_basis_prod( vector_a, basis_a )
	except Exception:
		vector_a_a = vector_a

	try:
		vector_b_b = vector_basis_prod( vector_b, basis_b )
	except Exception:
		vector_b_b = vector_b

	cosAngle = math.cos( angle_between( vector_a_a, vector_b_b, True ) )

	return length( vector_a_a ) * length( vector_b_b ) * cosAngle


def outter_prod_2D( vector_a, vector_b ):
	"""
	Calculates the outter product of the two vectors passed as arguments, both of which are expected to have
	orthonormal basis.

		:param vector_a: Two-element list or tuple of floats, integers or double values
		:param vector_b: Two-element list or tuple of floats, integers or double values

		:return: Float. The area of the parallelepiped formed by the two vectors

		raise: Exception
	"""

	try:
		return vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]
	except IndexError:
		raise Exception( "Expected 2 vectors of length 2 each. Exiting..." )


def outter_prod_3D( vector_a, vector_b, vector_c ):
	"""
	Calculates the outter product of the three vectors passed as arguments, all of which are expected to have
	orthonormal basis.

		:param vector_a: Three-element list or tuple of floats, integers or double values
		:param vector_b: Three-element list or tuple of floats, integers or double values
		:param vector_c: Three-element list or tuple of floats, integers or double values

		:return: Float. The volume of the parallelepiped formed by the three vectors

		:raise: Exception
	"""

	try:
		c1 = vector_a[0] * vector_b[1] * vector_c[2]
		c2 = vector_b[0] * vector_c[1] * vector_a[2]
		c3 = vector_c[0] * vector_a[1] * vector_b[2]
		c4 = vector_c[0] * vector_b[1] * vector_a[2]
		c5 = vector_b[0] * vector_a[1] * vector_c[2]
		c6 = vector_a[0] * vector_c[1] * vector_b[2]

		return c1 + c2 + c3 - c4 - c5 - c6
	except IndexError:
		raise Exception( "Vectors are expected to be in R3. Exiting..." )


def vector_projection_on_plane( vector, basis_a, basis_b, origin=( 0.0, 0.0, 0.0 ) ):
	"""
	Projects the vector passed as first argument on the plane formed by arguments passed for the basis_a (vector) and
	basis_b (vector) parameters and returns the coordinates for its projection in the space spanned by the basis as well
	as its coordinates in the vector\'s space.

		:param vector: List or tuple of floats
		:param basis_a: List or tuple of floats
		:param basis_b: List or tuple of floats
		:param origin: List or tuple of floats

		:return: List containing the projection vector\'s coordinates (list) in the space spanned by the basis as the
				first element and its coordinates (list) in the basis\'s space as the second element.
	"""

	vector = vector_sub( vector, origin )
	basis_a = vector_sub( basis_a, origin )
	basis_b = vector_sub( basis_b, origin )

	w = inner_prod( basis_a, basis_b )
	g = inner_prod( vector, basis_a )
	h = inner_prod( vector, basis_b )
	l = inner_prod( basis_a, basis_a )
	m = inner_prod( basis_b, basis_b )

	x = ( m * g - w * h ) / ( l * m + w * w )
	y = ( h - w * x ) / m

	return [
		[ x, y ],
		vector_add( vector_add( vector_scalar_prod( basis_a, x ), vector_scalar_prod( basis_b, y ) ), origin )
	]