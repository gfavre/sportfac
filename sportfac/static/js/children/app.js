
// Declare app level module which depends on filters, and services
angular.module('children', [ 'children.services', 'ngCookies', '$strap.directives']).
  config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/edit/:childId', {templateUrl: '/static/partials/child-detail.html', controller: 'childDetailCtrl'});
    $routeProvider.when('/new', {templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});

    $routeProvider.otherwise({templateUrl: '/static/partials/add-child.html', controller: 'childAddCtrl'});
  }]).
  config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[{');
    $interpolateProvider.endSymbol('}]}');
  }).value('$strapConfig', {
    datepicker: {
      language: 'fr',
      format: 'dd/MM/yyyy'
    }
});

var ListCtrl = function ($scope, $routeParams, $http) {
  $scope.routeParams = $routeParams;

  $scope.loadChildren = function(){
    $http.get('/api/family/').
      success(function(data, status, headers, config ){ 
        angular.forEach(data, function(child){
          if (child.id === parseInt($scope.routeParams.childId)) {
            child.selected = true;
            $scope.selectedChild = child;
          } else {
              child.selected = false;
          }
        });
        $scope.userChildren = data;
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
  }
  
  $scope.toHarmos = function(year) {
    return {1: "1re HARMOS",
            2: "2e HARMOS",
            3: "3e HARMOS",
            4: "4e HARMOS",
            5: "5e HARMOS",
            6: "6e HARMOS",}[year];
    
  };
  
};


var childDetailCtrl = function ($scope, ModelUtils,  $routeParams, $location) {
  $scope.detailedChild = {};
  this.initialValue = {};
  $scope.errors = {}
  $scope.reloadChild = function(){    
    ModelUtils.get('/api/children/', $routeParams.childId).then(function(child){
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
    ModelUtils.save('/api/children/', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };
  
  $scope.delChild = function(){
     ModelUtils.del('/api/children/', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };
  
  $scope.resetForm = function(){
      alert('reset detail');
      $scope.detailedChild = {};
  };

  $scope.hasNotChanged = function() {
    return angular.equals(this.initialValue, $scope.detailedChild);
  }
  
  
  
};

var childAddCtrl = function($scope, $location, ModelUtils){
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
    ModelUtils.save('/api/children/', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $scope.detailedChild = {}
      $location.url('/new');
    });
  };
}