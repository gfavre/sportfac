angular.module('sportfacChildren.controllers', [])

.controller('ListCtrl', ["$scope", "$routeParams", "$http", "ChildrenService",
function($scope, $routeParams, $http, ChildrenService) {
  'use strict';
  $scope.routeParams = $routeParams;

  $scope.loadChildren = function(){
    ChildrenService.all().then(function(children){
      $scope.userChildren = children;
      angular.forEach(children, function(child){
        if (child.id === parseInt($scope.routeParams.childId, 10)) {
            child.selected = true;
            $scope.selectedChild = child;
        } else {
            child.selected = false;
        }
      });
    });
  };
  
  $scope.loadTeachers = function(){
    $http.get('/api/teachers/').
      success(function(data, status, headers, config ){
        $scope.teachers = data;
    });
  };
  
  $scope.teachers = [];
  $scope.loadTeachers();
  
  
  $scope.loadChildren();
  
  $scope.selectChild = function(child){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = child;
    $scope.selectedChild.selected = true;
  };
  $scope.unselectChild = function(){
     if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = undefined;
  };
  
  $scope.toHarmos = function(year) {
    return {1: "1P HARMOS",
            2: "2P HARMOS",
            3: "3P HARMOS",
            4: "4P HARMOS",
            5: "5P HARMOS",
            6: "6P HARMOS",
            7: "7P HARMOS",
            8: "8P HARMOS",}[year];
    
  };
}])

.controller('childDetailCtrl', ["$scope", "$routeParams", "$location", "ChildrenService",
function($scope, $routeParams, $location, ChildrenService) {
  'use strict';
  $scope.detailedChild = {};
  this.initialValue = {};
  $scope.errors = {};
  
  $scope.reloadChild = function(){
    ChildrenService.get($routeParams.childId).then(function(child){
      for (var i=0; i< $scope.teachers.length; i++){
        var teacher = $scope.teachers[i];
        if (teacher.id === child.teacher){
          child.teacher = teacher;
          break;
        }
      }
      $scope.detailedChild = child;
      $scope.initialValue = angular.copy(child);
    });
  };
  $scope.reloadChild();

  $scope.updateSchoolYear = function(){
    $scope.detailedChild.school_year = $scope.detailedChild.teacher.years[0];
  };
  
  
  $scope.saveChild = function(){
    ChildrenService.save($scope.detailedChild).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };
  
  $scope.delChild = function(){
     ChildrenService.del($scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };
  
  $scope.resetForm = function(){
      $scope.detailedChild = {};
  };

  $scope.hasNotChanged = function() {
    return angular.equals(this.initialValue, $scope.detailedChild);
  };
}])
.controller('childAddCtrl', ["$scope", "$location", "ChildrenService",
function($scope, $location, ChildrenService) {
  $scope.unselectChild();
  $scope.detailedChild = {};
  $scope.errors = {};
  $scope.resetForm = function(){
    $scope.detailedChild = {};
  };
  $scope.updateSchoolYear = function(){
    $scope.detailedChild.school_year = $scope.detailedChild.teacher.years[0];
  };
  
  $scope.saveChild = function(){
    ChildrenService.save($scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $scope.detailedChild = {};
      $location.url('/new');
    });
  };
}]);