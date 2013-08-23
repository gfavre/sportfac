angular.module('sportfacChildren.services', []).

factory('ModelUtils', ["$http", "$cookies", function($http, $cookies){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };
        
    var ModelUtils = {
        /*get: function(url, id) {
          $http.get(url + id + '/').
            success(
            function(data, status, headers, config) { return data });
        },*/
        get: function(url, id){
          return $http.get(url + id + '/').then(function(response){
            return response.data;
          });
          
        },
        create: function(url, obj, errors){
          return $http.post(url, obj).
            success(function(response){
                angular.extend(obj, response);
            }).
            error(function(response, status){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(url + obj.id + '/', obj).
                     success(function(response){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(url, obj, errors);
          }
        },
        del: function(url, obj){
          return $http.delete(url + obj.id + '/');
        }
    };
    return ModelUtils;
}]);