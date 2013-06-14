'use strict';

/* Services */


// Demonstrate how to register services
// In this case it is a simple value service.
angular.module('children.services', []).
  value('version', '0.1').
  factory('ModelUtils', function($http, $cookies, $filter){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;

    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };
    
    var clean = function(elem){
       var copied = angular.copy(elem);
       copied.birth_date = $filter('date')(elem.birth_date, 'dd/MM/yyyy');
       copied.teacher = elem.teacher.id;
       
       return copied
    }
    
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
            success(function(response, status, headers, config){
                angular.extend(obj, response);
            }).
            error(function(response, status, headers, config){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          var cleaned = clean(obj);
          if (angular.isDefined(cleaned.id)){
            return $http.put(url + cleaned.id + '/', cleaned).
                     success(function(response, status, headers, config){
                        angular.extend(cleaned, response);
                     }).
                     error(function(response, status, headers, config){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(url, cleaned, errors);
          }
        },
        del: function(url, obj){
          return $http.delete(url + obj.id + '/');  
        }
    };
    return ModelUtils;

  });

