'use strict';

/* Services */


// Demonstrate how to register services
// In this case it is a simple value service.
angular.module('children.services', []).
  value('version', '0.1').
  factory('Child', function($http){
    var Child = function(data){
      angular.extend(this, data);
    }
    
    Child.get = function(id) {
      return $http.get('/api/family/' + id).then(function(response) {
        return new Child(response.data);
      });
    };

  // an instance method to create a new Book
  Child.prototype.create = function() {
    var child = this;
    return $http.post('/api/family/', child).then(function(response) {
      child.id = response.data.id;
      return child;
    });
  }
    
    
    return Child;
  });

