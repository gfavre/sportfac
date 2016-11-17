angular.module('sportfacChildren.services', [])

.factory('ModelUtils', ["$http", "$cookies", function($http, $cookies){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };
        
    var ModelUtils = {
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
}])

.factory('Child', ['$filter', function($filter){
    var Child = function(data){
      angular.extend(this, {
        toModel: function(){
          var converted = angular.copy(this);
          if (converted.teacher && typeof converted.teacher === 'object'){
            converted.teacher = converted.teacher.id;
          }
          if (typeof converted.birth_date === 'object'){
            converted.birth_date = $filter('date')(converted.birth_date, 'yyyy-MM-dd');
          }
          return converted;
        }
      });
      
      angular.extend(this, data);
    };
    return Child;
  }])

.factory('ChildrenService', ["$http", "$cookies", "Child",
  function($http, $cookies, Child){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };

    var ModelUtils = {
        all: function(url){
          return $http.get(url).then(function(response){
            var children = [];
            angular.forEach(response.data, function(childData){
              children.push(new Child(childData));
            });
            return children;
          });
        },
        get: function(url, childId){
          return $http.get(url + childId + '/').then(function(response){
            return new Child(response.data);
          });
        },
        lookup: function(url, extId, errors){
            return $http.get(url + '?ext=' + extId).then(function(response){
                if (response.data.length === 1){
                    errors.notfound = false;
                    return new Child(response.data[0]);
                }
                errors.notfound = true;
            });
        },
        del: function(url, obj){
          return $http.delete(url + obj.id + '/');
        },
        create: function(url, obj, errors){
          var child = new Child(obj);
          return $http.post(url, child.toModel()).
            success(function(response){
                angular.extend(child, response);
            }).
            error(function(response, status){
                handleErrors(response, status, errors);
            });
        },
        save: function(url, obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(url + obj.id + '/', obj.toModel()).
                     success(function(response){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(url, obj, errors);
          }
        }
    };
    
    return ModelUtils;
  }]);
