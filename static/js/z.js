var csrftoken = $('meta[name=csrf-token]').attr('content');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    }
});

function makeAsyncCallZillow() {
        var form_data = {
	        'street_number': $('#street_number').val().replace(/'/g, "\\'"),
	        'route': $('#route').val().replace(/'/g, "\\'"),
	        'postal_code': $('#postal_code').val().replace(/'/g, "\\'"),
	        'locality': $('#locality_short').val().replace(/'/g, "\\'"),
	        'administrative_area_level_1': $('#administrative_area_level_1').val().replace(/'/g, "\\'"),
	        'country': $('#country_short').val().replace(/'/g, "\\'"),
        };
        $.ajax({
            url: '/_zillow_search_ajax',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(form_data),
            success: function(response) {
	            results = JSON.parse(response);

	            if (results.search) {
		            //$("#suggestions").html(results.suggestions);
		            window.location.href = "/search";
		    	}
				else if (results.status == 'Failed') {
					$('#search_icon').removeClass('fa-spin');
				    $('#search_icon').removeClass('fa-spinner');
				    $('#search_icon').addClass('fa-exclamation-triangle');
					$("#message").html(results.message);
				}
				else {
			    	window.location.href = results.match;
		    	}
			},
			error: function(error) {
				console.log(error);
			}
        });
}
