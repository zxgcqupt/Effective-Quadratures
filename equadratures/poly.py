"""The polynomial parent class."""
import numpy as np
from .stats import Statistics
from .polycs import Polycs
from .polylsq import Polyls 
from .polyreg import Polyreg
from .eqxmltools import savepoly
from .eqxmltools import openpoly
from .eqtextools import compileReport # check out pylatex!

class Poly(object):
    """
    The class defines a Poly object. It is the parent class to Polyreg, Polyint, Polylsq and Polycs.
    The main difference between these classes is the way they compute polynomial coefficients.

    :param Parameter parameters:
        A list of parameters.
    :param Basis basis:
        A basis selected for the multivariate polynomial.
    :param string task:
        A user-defined task and sub-task. The task is the action while the sub-task defines the strategy. If a sub-task is not selected, a default option is chosen.
    :param function:
        The function on which the task must be executed. 
    :param gradfunction:
        The gradient function to be used for executing the task, for e.g., in an optimization context we would use gradfunction to specifiy search directions.
    :param string openfile
        An .eq file that should be read in.
    :param ndarray inputs
        A numpy ndarray of inputs of size m x d, where m represents the number of evaluations and d the dimension of the problem---equivalent to the number of parameters.
    :param ndarray outputs
        A numpy ndarray of outputs of size m x k, where m represents the number of evaluations and k>=1 the size of each output vector. In the case where k=1, we have scalar valued outputs.
    :param ndarray rankcorrrelation
        A numpy ndarray corresponding to a d x d linear rank correlation matrix.

    **Sample constructors**

    # DIMENSION REDUCTION
    myPoly = Poly(myParameters, myBasis, 'dimension-reduction:scalar', inputs,  outputs)
    >> e, W = myPoly.getActiveSubspaces()
    >> W = myPoly.getLinearModelSlope()
    >> W = myPoly.getRidgeApproximation(n=2)
    >> W = myPoly.getRidgeApproximation(n=1)
    myPoly = Poly(myParameters, myBasis, 'dimension-reduction:vector', inputs,  outputs)

    # UNCERTAINTY QUANTIFICATION
    myPoly = Poly(myParameters, myBasis, 'uncertainty-quantification:least-squares', function)
    myPoly = Poly(myParameters, myBasis, 'uncertainty-quantification:least-squares', function, gradfunction)
    myPoly = Poly(myParameters, myBasis, 'uncertainty-quantification:compressed-sensing', function)
    myPoly = Poly(myParameters, myBasis, 'uncertainty-quantification:least-squares', function, rankcorrelation)
    >> myStats = myPoly.getStatistics()
    
    # REGRESSION
    myPoly = Poly(myParameters, myBasis, 'regression:pca', inputs, outputs)
    myPoly = Poly(myParameters, myBasis, 'regression', inputs, outputs)
    >> model = myPoly.getPolyFitFunction()
    >> testing_outputs = model(training_inputs)

    # NUMERICAL INTEGRATION
    myPoly = Poly(myParameters, myBasis, 'numerical-integration:sparse-grids', function)
    myPoly = Poly(myParameters, myBasis, 'numerical-integration:near-optimal', function)
    >> points, weights = myPoly.getIntegrationPointsandWeights()
    >> integral = myPoly.getIntegral()

    # OPTIMIZATION
    myPoly = Poly(myParameters, 'optimize:polymin', function)
    myPoly = Poly(myParameters, 'optimize:sd', inputs, outputs)
    
    # I/O
    myPoly.save('myPoly.eq')
    myPoly = Poly(openfile='myPoly.eq')
    myPoly.compileReport()

    """
    def __init__(self, parameters, basis=None, task=None, inputs=None, outputs=None, function=None, gradfunction=None, rankcorrrelation=None, openfile=None):
        try:
            len(parameters)
        except TypeError:
            parameters = [parameters]
        self.parameters = parameters
        self.basis = basis
        self.dimensions = len(parameters)
        self.orders = []
        for i in range(0, self.dimensions):
            self.orders.append(self.parameters[i].order)
        if not self.basis.orders :
            self.basis.setOrders(self.orders)
        

        # Once the basic stuff has been specified. The code needs to compute coefficients, obviously the strategy will be
        # different depending on the problem. 

    def save(self, filename):
        """
        Saves a .eq file with all particulars about the polynomial. 
        :param Poly self:
            An instance of the Poly class.
        :param string filename:
            Filename to be used for saving.
        """
        savepoly(self, filename)
    def __setCoefficients__(self, coefficients):
        """
        Sets the coefficients for polynomial. This function will be called by the children of Poly
        :param Poly self:
            An instance of the Poly class.
        :param array coefficients:
            An array of the coefficients computed using either integration, least squares or compressive sensing routines.
        """
        self.coefficients = coefficients
    def __setBasis__(self, basisNew):
        """
        Sets the basis
        """
        self.basis = basisNew 
    def __setQuadrature__(self, quadraturePoints, quadratureWeights):
        """
        Sets the quadrature points and weights
        :param Poly self:
            An instance of the Poly class.
        :param matrix quadraturePoints:
            A numpy matrix filled with the quadrature points.
        :param matrix quadratureWeights:
            A numpy matrix filled with the quadrature weights.
        """
        self.quadraturePoints = quadraturePoints
        self.quadratureWeights = quadratureWeights
    def __setDesignMatrix__(self, designMatrix):
        """
        Sets the design matrix assocaited with the quadrature (depending on the technique) points and the polynomial basis.
        :param Poly self:
            An instance of the Poly class.
        :param matrix designMatrix:
            A numpy matrix filled with the multivariate polynomial evaluated at the quadrature points.
        """
        self.designMatrix = designMatrix
    def clone(self):
        """
        Clones a Poly object.
        :param Poly self:
            An instance of the Poly class.
        :return:
            A clone of the Poly object.
        """
        return type(self)(self.parameters, self.basis)
    def getPolynomial(self, stackOfPoints, customBases=None):
        """
        Evaluates the value of each polynomial basis function at a set of points.
        :param Poly self:
            An instance of the Poly class.
        :param matrix stackOfPoints:
            A N-by-d matrix of points along which the multivariate (in d-dimensions) polynomial basis functions must be evaluated.
        :return:
            A P-by-N matrix of polynomial basis function evaluations at the stackOfPoints, where P is the cardinality of the basis.
        """
        if customBases is None:
            basis = self.basis.elements
        else:
            basis = customBases
        basis_entries, dimensions = basis.shape

        if stackOfPoints.ndim == 1:
            no_of_points = 1
        else:
            no_of_points, __ = stackOfPoints.shape
        p = {}

        # Save time by returning if univariate!
        if dimensions == 1:
            poly , _ =  self.parameters[0]._getOrthoPoly(stackOfPoints, int(np.max(basis)))
            return poly
        else:
            for i in range(0, dimensions):
                if len(stackOfPoints.shape) == 1:
                    stackOfPoints = np.array([stackOfPoints])
                p[i] , _ = self.parameters[i]._getOrthoPoly(stackOfPoints[:,i], int(np.max(basis[:,i])) )

        # One loop for polynomials
        polynomial = np.ones((basis_entries, no_of_points))
        for k in range(dimensions):
            basis_entries_this_dim = basis[:, k].astype(int)
            polynomial *= p[k][basis_entries_this_dim]

        return polynomial
    def getPolynomialGradient(self, stackOfPoints, dim_index = None):
        """
        Evaluates the gradient for each of the polynomial basis functions at a set of points,
        with respect to each input variable.
        :param Poly self:
            An instance of the Poly class.
        :param matrix stackOfPoints:
            A N-by-d matrix of points along which the gradient of the multivariate (in d-dimensions) polynomial basis
            functions must be evaluated.
        :return:
            A list with d elements, each with a P-by-N matrix of polynomial evaluations at the stackOfPoints,
            where P is the cardinality of the basis.
        """
        # "Unpack" parameters from "self"
        basis = self.basis.elements
        basis_entries, dimensions = basis.shape
        no_of_points, _ = stackOfPoints.shape
        p = {}
        dp = {}

        # Save time by returning if univariate!
        if dimensions == 1:
            _ , dpoly =  self.parameters[0]._getOrthoPoly(stackOfPoints, int(np.max(basis) ) )
            return dpoly
        else:
            for i in range(0, dimensions):
                if len(stackOfPoints.shape) == 1:
                    stackOfPoints = np.array([stackOfPoints])
                p[i] , dp[i] = self.parameters[i]._getOrthoPoly(stackOfPoints[:,i], int(np.max(basis[:,i])) )

        # One loop for polynomials
        R = []
        if dim_index is None:
            dim_index = range(dimensions)
        for v in range(dimensions):
            if not(v in dim_index):
                R.append(np.zeros((basis_entries, no_of_points)))
            else:
                polynomialgradient = np.ones((basis_entries, no_of_points))
                for k in range(dimensions):
                    basis_entries_this_dim = basis[:,k].astype(int)
                    if k==v:
                        polynomialgradient *= dp[k][basis_entries_this_dim]
                    else:
                        polynomialgradient *= p[k][basis_entries_this_dim]
                R.append(polynomialgradient)

        return R
    def getTensorQuadratureRule(self, orders=None):
        """
        Generates a tensor grid quadrature rule based on the parameters in Poly.
        :param Poly self:
            An instance of the Poly class.
        :param list orders:
            A list of the highest polynomial orders along each dimension.
        :return:
            A numpy array of quadrature points.
        :return:
            A numpy array of quadrature weights.
        """
        # Initialize points and weights
        pp = [1.0]
        ww = [1.0]

        if orders is None:
            orders = self.basis.orders

        # number of parameters
        # For loop across each dimension
        for u in range(0, self.dimensions):

            # Call to get local quadrature method (for dimension 'u')
            local_points, local_weights = self.parameters[u]._getLocalQuadrature(orders[u])
            ww = np.kron(ww, local_weights)

            # Tensor product of the points
            dummy_vec = np.ones((len(local_points), 1))
            dummy_vec2 = np.ones((len(pp), 1))
            left_side = np.array(np.kron(pp, dummy_vec))
            right_side = np.array( np.kron(dummy_vec2, local_points) )
            pp = np.concatenate((left_side, right_side), axis = 1)

        # Ignore the first column of pp
        points = pp[:,1::]
        weights = ww

        # Return tensor grid quad-points and weights
        return points, weights
    def getStatistics(self, light=None, max_sobol_order=None):
        """
        Creates an instance of the Statistics class.
        :param Poly self:
            An instance of the Poly class.
        :param string quadratureRule:
            Two options exist for this string. The user can use 'qmc' for a distribution specific Monte Carlo (QMC) or they can use 'tensor grid' for standard tensor product grid. Typically, if the number of dimensions is less than 8, the tensor grid is the default option selected.
        :return:
            A Statistics object.
        """
        if light is None:
            evals = self.getPolynomial(self.quadraturePoints)
            return Statistics(self.coefficients, self.basis, self.parameters, self.quadraturePoints, self.quadratureWeights, evals, max_sobol_order)
        else:
            return Statistics(self.coefficients, self.basis, self.parameters, max_sobol_order=max_sobol_order)            
    def getQuadratureRule(self, options=None, number_of_points = None):
        """
        Generates quadrature points and weights.
        :param Poly self:
            An instance of the Poly class.
        :param string options:
            Two options exist for this string. The user can use 'qmc' for a distribution specific Monte Carlo (QMC) or they can use 'tensor grid' for standard tensor product grid. Typically, if the number of dimensions is less than 8, the tensor grid is the default option selected.
        :param int number_of_points:
            If QMC is chosen, specifies the number of quadrature points in each direction. Otherwise, this is ignored.
        :return:
            A numpy array of quadrature points.
        :return:
            A numpy array of quadrature weights.
        """
        if options is None:
            if self.dimensions > 5 or np.max(self.orders) > 4:
                options = 'qmc'
            else:
                options = 'tensor grid'
        if options.lower() == 'qmc':
            if number_of_points is None:
                default_number_of_points = 20000
            else:
                default_number_of_points = number_of_points
            p = np.zeros((default_number_of_points, self.dimensions))
            w = 1.0/float(default_number_of_points) * np.ones((default_number_of_points))
            for i in range(0, self.dimensions):
                p[:,i] = np.array(self.parameters[i].getSamples(default_number_of_points)).reshape((default_number_of_points,))
            return p, w

        if options.lower() == 'tensor grid' or options.lower() == 'quadrature':
            p,w = self.getTensorQuadratureRule([i for i in self.basis.orders])
            return p,w
    def evaluatePolyFit(self, stackOfPoints):
        """
        Evaluates the the polynomial approximation of a function (or model data) at prescribed points.
        :param Poly self:
            An instance of the Poly class.
        :param matrix stackOfPoints:
            A N-by-d matrix of points (can be unscaled) at which the polynomial gradient must be evaluated at.
        :return:
            A 1-by-N matrix of the polynomial approximation.
        """
        return self.getPolynomial(stackOfPoints).T *  np.mat(self.coefficients)
    def evaluatePolyGradFit(self, stackOfPoints):
        """
        Evaluates the gradient of the polynomial approximation of a function (or model data) at prescribed points.
        :param Poly self:
            An instance of the Poly class.
        :param matrix stackOfPoints:
            A N-by-d matrix of points (can be unscaled) at which the polynomial gradient must be evaluated at.
        :return:
            A d-by-N matrix of the gradients of the polynomial approximation.
        **Notes:**
        This function should not be confused with getPolynomialGradient(). The latter is only concerned with approximating what the multivariate polynomials
        gradient values are at prescribed points.
        """
        H = self.getPolynomialGradient(stackOfPoints)
        grads = np.zeros((self.dimensions, len(stackOfPoints) ) )
        for i in range(0, self.dimensions):
            grads[i,:] = np.mat(self.coefficients).T * H[i]
        return grads
    def getPolyFitFunction(self):
        """
        Returns a callable polynomial approximation of a function (or model data).
        :param Poly self:
            An instance of the Poly class.
        :return:
            A callable function.
        """
        return lambda (x): self.getPolynomial(x).T *  np.mat(self.coefficients)
    def getPolyGradFitFunction(self):
        """
        Returns a callable for the gradients of the polynomial approximation of a function (or model data).
        :param Poly self:
            An instance of the Poly class.
        :return:
            A callable function.
        """
        return lambda (x) : self.evaluatePolyGradFit(x)
    def getFunctionSamples(self, number_of_samples):
        """
        Returns a set of function samples; useful for computing probabilities.
        :param Poly self:
            An instance of the Poly class.
        :param callable function:
            A callable function (or evaluations of the function at the prerequisite quadrature points).
        :param array coefficients:
            A numpy array of the coefficients
        :param matrix indexset:
            A K-by-d matrix of the index set.
        :return:
            A 50000-by-1 array of function evaluations.
        """
        dimensions = self.dimensions
        if number_of_samples is None:
            number_of_samples = 50000 # default value!
        plotting_pts = np.zeros((number_of_samples, dimensions))
        for i in range(0, dimensions):
                univariate_samples = self.parameters[i].getSamples(number_of_samples)
                for j in range(0, number_of_samples):
                    plotting_pts[j, i] = univariate_samples[j]
        samples = self.evaluatePolyFit(plotting_pts)
        return plotting_pts, samples