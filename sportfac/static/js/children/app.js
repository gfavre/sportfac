
// Declare app level module which depends on filters, and services
angular.module('children', [ 'children.services', 'ngCookies', '$strap.directives']).
  config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/edit/:childId', {templateUrl: '/static/partials/child-detail.html', controller: 'childDetailCtrl'});
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

var ListCtrl = function ($scope, $http) {
  $scope.loadChildren = function(){
    $http.get('/api/family/').
      success(function(data, status, headers, config ){ 
        $scope.userChildren = data;
    });
  };
  
  $scope.selectedChild = {};
  $scope.loadChildren();
  
  $scope.selectChild = function(child){
    if ($scope.selectedChild){
        $scope.selectedChild.selected = false;
    }
    $scope.selectedChild = child;
    $scope.selectedChild.selected = true;
  };

  
};


var childDetailCtrl = function ($scope, ModelUtils,  $routeParams, $location) {
  ModelUtils.get('/api/children/', $routeParams.childId).then(function(child){
    $scope.detailedChild = child;
  });
  
  $scope.errors = {}
  $scope.saveChild = function(){ 
    ModelUtils.save('/api/children/', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };
  
  $scope.delChild = function(){
     ModelUtils.del('/api/children', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      
    });
  };  
};

var childAddCtrl = function($scope, ModelUtils){
    $scope.detailedChild = {};
    $scope.errors = {}
    $scope.saveChild = function(){ 
      ModelUtils.save('/api/children/', $scope.detailedChild, $scope.errors).then(function(){
      $scope.loadChildren();
      $scope.selectedChild = {};
      $location.url('/');
    });
  };


}