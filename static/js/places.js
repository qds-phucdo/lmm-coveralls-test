/* Google Places */
  var placeSearch, autocomplete;
  var componentForm = {
    street_number: 'short_name',
    route: 'long_name',
    locality: 'long_name',
    locality_short: 'short_name',
    administrative_area_level_1: 'short_name',
    country: 'long_name',
    country_short: 'short_name',
    postal_code: 'short_name'
  };

  function initAutocomplete() {
    // Create the autocomplete object, restricting the search to geographical
    // location types.
    autocomplete = new google.maps.places.Autocomplete(
        /** @type {!HTMLInputElement} */(document.getElementById('autocomplete')),
        {types: ['geocode']});

    // When the user selects an address from the dropdown, populate the address
    // fields in the form.
    autocomplete.addListener('place_changed', fillInAddress);
  }

    $('#autocomplete').keypress(function(e) {
	  if (e.which == 13) {
	    google.maps.event.trigger(autocomplete, 'place_changed');
	    return false;
	  }
	});

  function fillInAddress() {
    $('#search_icon').removeClass('fa-search');
    $('#search_icon').removeClass('fa-exclamation-triangle');
    $('#search_icon').addClass('fa-spin');
    $('#search_icon').addClass('fa-spinner');

    // Get the place details from the autocomplete object.
    var place = autocomplete.getPlace();
    
    for (var component in componentForm) {
      document.getElementById(component).value = '';
      document.getElementById(component).disabled = false;
    }

    // Get each component of the address from the place details
    // and fill the corresponding field on the form.
    for (var i = 0; i < place.address_components.length; i++) {
      var addressType = place.address_components[i].types[0];
      if (componentForm[addressType]) {
        var val = place.address_components[i][componentForm[addressType]];
        document.getElementById(addressType).value = val;
      }

      if (['country', 'locality'].indexOf(addressType) != -1) {
      	document.getElementById(addressType+ '_short').value = place.address_components[i]['short_name'];
      }
    }
    //get street number. If api can't get street number
    if($('#street_number').val() == '') {
    	var street_number =  $('#autocomplete').val().split(" ")[0];
    	$('#street_number').val(street_number);
    }
    // Let's get Zillow Search Results
    makeAsyncCallZillow()
  }

  // Bias the autocomplete object to the user's geographical location,
  // as supplied by the browser's 'navigator.geolocation' object.
  function geolocate() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(position) {
        var geolocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };
        var circle = new google.maps.Circle({
          center: geolocation,
          radius: position.coords.accuracy
        });
        autocomplete.setBounds(circle.getBounds());
      });
    }
  }
