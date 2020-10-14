## This function checks for overfitting (difference between train and test data)
# @param X_train list | Training data 
# @param X_test list | Test data 
# @param y_train list | Training labels 
# @param y_test list | Test labels 
# @param fitted_model sklearn.linear_model._base.LinearRegression | Trained model
# @param metric function | Overfitting function, e.g. mean_squared_error
def overfit_check(X_train, X_test, y_train, y_test,
                  fitted_model, metric):
    
    y_pred = fitted_model.predict(X_test)
    y_train_pred = fitted_model.predict(X_train)
    
    return metric(y_test, y_pred) - metric(y_train, y_train_pred)

## This function returns accuracy 
# @param X_train list | Training data 
# @param X_test list | Test data 
# @param y_train list | Training labels 
# @param y_test list | Test labels 
# @param fitted_model sklearn.linear_model._base.LinearRegression | Trained model
# @param metric function | Accuracy function, e.g. r2_score
def accuracy_check(X_train, X_test, y_train, y_test, 
                   fitted_model, metric):
    
    y_pred = fitted_model.predict(X_test)
        
    return metric(y_test, y_pred)
        
## This function checks for homoscedascity  
# @param X_train list | Training data 
# @param X_test list | Test data 
# @param y_train list | Training labels 
# @param y_test list | Test labels 
# @param fitted_model sklearn.linear_model._base.LinearRegression | Trained model
def homoscedascity_check(X_train, X_test, y_train, y_test, 
                         fitted_model):
    
    prediction_residual_pairs = []
    y_pred = fitted_model.predict(X_test)
        
    for i in range(len(y_test)):
        prediction_residual_pairs.append([y_pred[i], y_test[i] - y_pred[i]])
        
    return prediction_residual_pairs