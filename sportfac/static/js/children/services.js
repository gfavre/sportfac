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
}])

.factory('Child', ['$filter', function($filter){
    var Child = function(data){
      angular.extend(this, {
        toModel: function(){
          var converted = angular.copy(this);
          if (typeof converted.teacher === 'object'){
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

.factory('ChildrenService', ["$http", "$cookies", "Child", function($http, $cookies, Child){
    $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
    var base = '/api/children/';
    var handleErrors = function(serverResponse, status, errorDestination){
      if (angular.isDefined(errorDestination)){
        angular.forEach(serverResponse, function(value, key){
          errorDestination[key] = value;
        });
      }
    };

    var ModelUtils = {
        all: function(){
          return $http.get('/api/family/').then(function(response){
            var children = [];
            angular.forEach(response.data, function(childData){
              children.push(new Child(childData));
            });
            return children;
          });
        },
        get: function(childId){
          return $http.get(base + childId + '/').then(function(response){
            return new Child(response.data);
          });
        },
        lookup: function(extId){
            return $http.get(base + '?ext=' + extId).then(function(response){
                return new Child(response.data)
            });
        },
        del: function(obj){
          return $http.delete(base + obj.id + '/');
        },
        create: function(obj, errors){
          var child = new Child(obj);
          return $http.post(base, child.toModel()).
            success(function(response){
                angular.extend(child, response);
            }).
            error(function(response, status){
                handleErrors(response, status, errors);
            });
        },
        save: function(obj, errors){
          if (angular.isDefined(obj.id)){
            return $http.put(base + obj.id + '/', obj.toModel()).
                     success(function(response){
                        angular.extend(obj, response);
                     }).
                     error(function(response, status){
                       handleErrors(response, status, errors);
                     });
          } else {
            return this.create(obj, errors);
          }
        },
    };
    
    return ModelUtils;
  }]);
