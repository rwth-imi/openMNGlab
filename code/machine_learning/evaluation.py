# -*- coding: utf-8 -*-


def overfit_check(X_train, X_test, y_train, y_test,
                  fitted_model, metric):
    
    y_pred = fitted_model.predict(X_test)
    y_train_pred = fitted_model.predict(X_train)
    
    return metric(y_test, y_pred) - metric(y_train, y_train_pred)

        
def accuracy_check(X_train, X_test, y_train, y_test, 
                   fitted_model, metric):
    
    y_pred = fitted_model.predict(X_test)
        
    return metric(y_test, y_pred)
        

def homoscedascity_check(X_train, X_test, y_train, y_test, 
                         fitted_model):
    
    prediction_residual_pairs = []
    y_pred = fitted_model.predict(X_test)
        
    for i in range(len(y_test)):
        prediction_residual_pairs.append([y_pred[i], y_test[i] - y_pred[i]])
        
    return prediction_residual_pairs