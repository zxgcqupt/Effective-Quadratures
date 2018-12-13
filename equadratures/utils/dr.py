
"""The functionalities of this script includes:
    1. A polynomial-based active subspaces recipe;
    2. An ordinary least squares linear technique;
    3. The variable projection subroutine.

References:
    - Honkason, J. and Constantine, P. (2018). Data-driven polynomial ridge approximation using variable projection. [online] Arxiv.org. `Paper <https://arxiv.org/abs/1702.05859>`_.
    - Constantine, P. G. (2015). Active subspaces: Emerging ideas for dimension reduction in parameter studies. SIAM.
"""
import numpy as np
import scipy
from parameter import Parameter
from poly import Poly
import scipy.io
from basis import Basis
from scipy.linalg import orth

class dr(object):
    def __init__(self, poly=None, training_input=None, training_output=None):
        if poly is not None:
            self.poly = poly
        if training_input is not None:
            self.training_input = training_input
        if training_output is not None:
            self.training_output = training_output

    def computeActiveSubspaces(self, poly=None, samples=None, alpha=None, k=None):
        """
        Computes the eigenvalues and corresponding eigenvectors for the high dimensional kernel matrix via polynomial model.

        :param PolynomialObject: an instance of PolynomialObject class
        :param samples: ndarray, sample vector points, default to None
        :return:
            * **eigs (numpy array)**: Eigenvalues obtained
            * **eigVecs (numpy array)**: Eigenvectors obtained
        """
        if not(hasattr(self,'poly')) and poly is None:
            raise Exception('Must declare poly!')
        elif poly is None:
            poly = self.poly

        if samples is None:
            d = poly.dimensions
            if alpha is None:
                alpha = 4
            if k is None or k > d:
                k = d
            M = alpha * k * np.log(d)
            X = np.zeros((M, d))
            for j in range(0, d):
                X[:, j] =  np.reshape(poly.parameters[j].getSamples(M), M)
        else:
            X = samples
            M, _ = X.shape
            X = samples

        # Gradient matrix!
        polygrad = poly.evaluatePolyGradFit(X)
        weights = np.ones((M, 1)) / M
        R = polygrad.transpose() * weights
        C = np.dot(polygrad, R )

        # Compute eigendecomposition!
        e, W = np.linalg.eigh(C)
        idx = e.argsort()[::-1]
        eigs = e[idx]
        eigVecs = W[:, idx]
        return eigs, eigVecs

    def linearModel(self, training_input=None, training_output=None):
        """
        Computes the coefficients for a linear model between inputs and outputs

        :param Xtrain: ndarray, the input values
        :param ytrain: array, the output values
        :return:
            * **u (numpy array)**: Coefficients correspond to each dimension
            * **c (double)**: Constant bias
        """
        if training_input is None:
            training_input = self.training_input
        if training_output is None:
            training_output = self.training_output
        if training_input is None or training_output is None:
            raise Exception('training data missing!')
        N,D=training_input.shape
        A=np.concatenate((training_input,np.ones((N,1))),axis=1)
        x=np.linalg.lstsq(A,training_output)[0]
        u=x[0:D-1]
        c=x[D]
        return u,c

    def standard(self,bounds,X=None):
        """
        Standardize the inputs before Dimension Reduction

        :param X: ndarray, the undimensioned input values
        :param bounds: ndarray, the upper and lower bounds for input values in each dimension
        :return:
            * **X_stnd (numpy array)**: Standardized input values
        """
        update_self = False
        if X is None:
            X = self.training_input
            update_self = True
        M,m=X.shape
        X_stnd=np.zeros((M,m))
        for i in range(0,M):
            for j in range(0,m):
                X_stnd[i,j]=2*(X[i,j]-bounds[j,0])/(bounds[j,1]-bounds[j,0])-1
        if update_self:
            self.training_input = X_stnd.copy()
        return X_stnd

    @staticmethod
    def vandermonde(eta,p):
        """
        Internal function to variable_projection
        Calculates the Vandermonde matrix using polynomial basis functions

        :param eta: ndarray, the affine transformed projected values of inputs in active subspace
        :param p: int, the maximum degree of polynomials
        :return:
            * **V (numpy array)**: The resulting Vandermode matrix
            * **Polybasis (Poly object)**: An instance of Poly object containing the polynomial basis derived
        """
        _,n=eta.shape
        listing=[]
        for i in range(0,n):
            listing.append(p)
        Object=Basis('Total order',listing)
        #Establish n Parameter objects
        params=[]
        P=Parameter(order=p,lower=-1,upper=1,distribution='uniform')
        for i in range(0,n):
            params.append(P)
        #Use the params list to establish the Poly object
        Polybasis=Poly(params,Object)
        V=Polybasis.getPolynomial(eta)
        V=V.T
        return V,Polybasis

    @staticmethod
    def jacobian(V,V_plus,U,y,f,Polybasis,eta,minmax,X):
        """
        Internal function to variable_projection
        Calculates the Jacobian tensor using polynomial basis functions

        :param V: ndarray, the affine transfored outputs
        :param V_plus: ndarray, psuedoinverse matrix
        :param U: ndarray, the active subspace directions
        :param y: array, the untransformed projected values of inputs in active subspace
        :param f: array, the untransfored outputs
        :param Polybasis: Poly object, an instance of Poly class
        :param eta: ndarray, the affine transformed projected values of inputs in active subspace
        :param minmax: ndarray, the upper and lower bounds of input projections in each dimension
        :param X: ndarray, the input
        :return:
            * **J (ndarray)**: The Jacobian tensor
        """
        M,N=V.shape
        m,n=U.shape
        Gradient=Polybasis.getPolynomialGradient(eta)
        sub=(minmax[1,:]-minmax[0,:]).T# n*1 array
        vectord=np.reshape(2.0/sub,(n,1))
        #Initialize the tensor
        J=np.zeros((M,m,n))
        #Obtain the derivative of this tensor
        dV=np.zeros((m,n,M,N))
        for k in range(0,m):
            for l in range(0,n):
                for i in range(0,M):
                    for j in range(0,N):
                        current=Gradient[l].T
                        if n==1:
                            current=Gradient.T
                        dV[k,l,i,j]=np.asscalar(vectord[l])*np.asscalar(X[i,k])*np.asscalar(current[i,j])#Eqn 16 17
        #Get the P matrix
        P=np.identity(M)-np.matmul(V,V_plus)
        V_minus=scipy.linalg.pinv(V)
        #Calculate entries for the tensor
        for j in range(0,m):
            for k in range(0,n):
                temp1=np.linalg.multi_dot([P,dV[j,k,:,:],V_minus])
                J[:,j,k]=(-np.matmul((temp1+temp1.T),f)).reshape((M,))# Eqn 15
        return J

    def variable_projection(self,n,p,X=None,f=None,gamma=None,beta=None,tol=None,maxiter=1000):
        """
        Variable Projection function to obtain an active subspace in inputs design space

        :param X: ndarray, the input
        :param f: array, the output
        :param n: int, number of active subspace directions to calculate
        :param p: int, degree of polynomials
        :param gamma: double, step length reduction factor (0,1)
        :param beta: double, Armijo tolerance for backtracking line search (0,1)
        :param tol: double, tolerance for convergence, measured in the norm of residual over norm of f
        :return:
            * **U (ndarray)**: The active subspace found
            * **R (double)**: Cost of deviation in fitting
        """
        if gamma is None:
            gamma=0.1
        if beta is None:
            beta=0.1
        if X is None:
            X = self.training_input
        if f is None:
            f = self.training_output
        if X is None or f is None:
            raise Exception('Missing training data!')
        M,m=X.shape
        Z=np.random.randn(m,n)
        U,_=np.linalg.qr(Z)

        y=np.dot(X,U)
        minmax=np.zeros((2,n))
        for i in range(0,n):
            minmax[0,i]=min(y[:,i])
            minmax[1,i]=max(y[:,i])
        #Construct the affine transformation
        eta=np.zeros((M,n))
        for i in range(0,M):
            for j in range(0,n):
                eta[i,j]=2*(y[i,j]-minmax[0,j])/(minmax[1,j]-minmax[0,j])-1

        #Construct the Vandermonde matrix step 6
        V,Polybasis=self.vandermonde(eta,p)
        V_plus=np.linalg.pinv(V)
        coeff=np.dot(V_plus,f)
        res=f-np.dot(V,coeff)
        R=np.linalg.norm(res)
        #TODO: convergence criterion??
        for iteration in range(0,maxiter):
            #Construct the Jacobian step 9
            J=self.jacobian(V,V_plus,U,y,f,Polybasis,eta,minmax,X)
            #Calculate the gradient of Jacobian #step 10
            G=np.zeros((m,n))
            for i in range(0,M):
                G=G+res[i]*J[i,:,:]
            #conduct the SVD for J_vec
            vec_J=np.zeros((M,(m*n)))
            for i in range(0,M):
                for j in range(0,m):
                    for k in range(0,n):
                        vec_J[i,j*n+k]=J[i,j,k]
            Y,S,Z=np.linalg.svd(vec_J,full_matrices=False)#step 11
            #obtain delta
            delta = np.dot(Y[:,:-n**2].T, res)
            delta = np.dot(np.diag(1/S[:-n**2]), delta)
            delta = -np.dot(Z[:-n**2,:].T, delta).reshape(U.shape)
            #carry out Gauss-Newton step
            vec_delta=delta.flatten()# step 12
            #vectorize G step 13
            vec_G=G.flatten()
            alpha=np.dot(vec_G.T,vec_delta)
            norm_G=np.dot(vec_G.T,vec_G)
            #check alpha step 14
            if alpha>=0:
                delta=-G
                alpha=-norm_G

            #SVD on delta step 17
            Y,S,Z=np.linalg.svd(delta,full_matrices=False)
            UZ=np.dot(U,Z.T)
            t=1
            for iter2 in range(0,50):
                U_new=np.dot(UZ, np.diag(np.cos(S*t))) + np.dot(Y, np.diag(np.sin(S*t)))#step 19
                U_new=orth(U_new)
                #Update the values with the new U matrix
                y=np.dot(X,U_new)
                minmax=np.zeros((2,n))
                for i in range(0,n):
                    minmax[0,i]=min(y[:,i])
                    minmax[1,i]=max(y[:,i])
                eta=np.zeros((M,n))
                for i in range(0,M):
                    for j in range(0,n):
                        eta[i,j]=2*(y[i,j]-minmax[0,j])/(minmax[1,j]-minmax[0,j])-1
                V_new,Polybasis=self.vandermonde(eta,p)
                V_plus_new=np.linalg.pinv(V_new)
                coeff_new=np.dot(V_plus_new,f)
                res_new=f-np.dot(V_new,coeff_new)
                R_new=np.linalg.norm(res_new)
                if np.linalg.norm(res_new)<=np.linalg.norm(res)+alpha*beta*t or t<1e-10:#step 21
                    break
                t=t*gamma
            U = U_new
            V = V_new
            coeff = coeff_new
            res = res_new
            R = R_new

            if not(tol is None):
                if R < tol:
                    break
        return U,R
