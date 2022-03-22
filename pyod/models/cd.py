# -*- coding: utf-8 -*-
"""Cook's distance outlier detection (CD)
"""

# Author: D Kulik
# License: BSD 2 clause

from __future__ import division
from __future__ import print_function

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from sklearn.utils import check_array
from sklearn.utils.validation import check_is_fitted

from .base import BaseDetector
from ..utils.utility import check_parameter

def whiten_data(X, pca):

    X = pca.transform(X)

    return X


def Cooks_dist(X, y, model):
    
    # Leverage is computed as the diagonal of the projection matrix of X
    leverage = (X * np.linalg.pinv(X).T).sum(1)

    # Compute the rank and the degrees of freedom of the model
    rank = np.linalg.matrix_rank(X)
    df = X.shape[0] - rank

    # Compute the MSE from the residuals
    residuals = y - model.predict(X)
    mse = np.dot(residuals, residuals) / df

    # Compute Cook's distance
    residuals_studentized = residuals / np.sqrt(mse) / np.sqrt(1 - leverage)
    distance_ = residuals_studentized ** 2 / X.shape[1]
    distance_ *= leverage / (1 - leverage)

    return distance_

    

class CD(BaseDetector):
    """Cook's distance can be used to identify points that negatively
       affect a regression model. A combination of each observation’s
       leverage and residual values are used in the measurement. Higher
       leverage and residuals relate to  higher Cook’s distances.
       Read more in the :cite:`cook1977outlier`.

    Parameters
    ----------
    contamination : float in (0., 0.5), optional (default=0.1)
        The amount of contamination of the data set, i.e.
        the proportion of outliers in the data set. Used when fitting to
        define the threshold on the decision function.
        
    whiten : None or string ['PCA', 'ZCA', 'SVD'], optional (default=None)
        transform X to have a covariance matrix that is the identity matrix 
        of 1 in the diagonal and 0 for the other cells

    rule_of_thumb : bool, optional (default=False)
        to apply the rule of thumb prediction (4 / n) as the influence
        threshold; where n is the number of samples. This has been know to
        be a good estimate for values over this point as being outliers.
        ** Note the contamination level is reset when rule_of_thumb is
           set to True
          

    Attributes
    ----------
    decision_scores_ : numpy array of shape (n_samples,)
        The outlier scores of the training data.
        The higher, the more abnormal. Outliers tend to have higher
        scores. This value is available once the detector is
        fitted.

    threshold_ : float
       The modified z-score to use as a threshold. Observations with
       a modified z-score (based on the median absolute deviation) greater
       than this value will be classified as outliers.

    labels_ : int, either 0 or 1
        The binary labels of the training data. 0 stands for inliers
        and 1 for outliers/anomalies. It is generated by applying
        ``threshold_`` on ``decision_scores_``.
        """


    def __init__(self, whitening=True, contamination=0.1, rule_of_thumb=False):

            super(CD, self).__init__(contamination=contamination)
            self.whitening = whitening
            self.rule_of_thumb = rule_of_thumb
            

    def fit(self, X, y):
        """Fit detector. y is necessary for supervised method.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The input samples.

        y : numpy array of shape (n_samples,), optional (default=None)
            The ground truth of the input samples (labels).
        """

        # Define OLS model 
        self.model = LinearRegression()

        # Validate inputs X and y
        try:
            X = check_array(X)
        except ValueError: 
            X = X.reshape(-1,1)
            
        y = np.squeeze(check_array(y, ensure_2d=False))
        self._set_n_classes(y)

        # Apply whitening
        if self.whitening:
            self.pca = PCA(whiten=True)
            self.pca.fit(X)
            X = whiten_data(X, self.pca)

        # Fit a linear model to X and y
        self.model.fit(X, y)

        # Get Cook's Distance
        distance_ = Cooks_dist(X, y, self.model)

        # Compute the influence threshold
        if self.rule_of_thumb:
            influence_threshold_ = 4 / X.shape[0]
            self.contamination = sum(distance_ > influence_threshold_) / X.shape[0]

        self.decision_scores_ = distance_

        self._process_decision_scores()

        return self


    def decision_function(self, X):
        """Predict raw anomaly score of X using the fitted detector.

        The anomaly score of an input sample is computed based on different
        detector algorithms. For consistency, outliers are assigned with
        larger anomaly scores.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The training input samples. Sparse matrices are accepted only
            if they are supported by the base estimator.

        Returns
        -------
        anomaly_scores : numpy array of shape (n_samples,)
            The anomaly score of the input samples.
        """

        check_is_fitted(self, ['decision_scores_', 'threshold_', 'labels_'])

        try:
            X = check_array(X)
        except ValueError: 
            X = X.reshape(-1,1)
        
        y = X[:,-1]
        X = X[:,:-1]
    

        # Apply whitening
        if self.whitening:
            X = whiten_data(X, self.pca) 

        # Get Cook's Distance
        distance_ = Cooks_dist(X, y, self.model)

        return distance_
