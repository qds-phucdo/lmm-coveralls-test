var csrftoken_inside = $('meta[name=csrf-token]').attr('content');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken_inside)
        }
    }
});

$("#lblrefresh").click(function() {
	var propertyAddress = $(this).data("address") ? $(this).data("address") : '';
	send_changed_value('refresh', '1.0', propertyAddress);
	$('#saveModalButton').removeClass("kv-icon-success");
	link_html = '<button type="button" class="btn btn-secondary generate-share-button">Generate Shareable Link</button>';
    $('#shareable_button').html(link_html);
});

$("#removesave").click(function() {
	var propertyAddress = $(this).data("address") ? $(this).data("address") : '';
	send_changed_value('refresh', '1.0', propertyAddress);
	$('#saveModalButton').removeClass("kv-icon-success");
	$('#saveModal').modal('toggle');
	link_html = '<button type="button" class="btn btn-secondary generate-share-button">Generate Shareable Link</button>';
    $('#shareable_button').html(link_html);
});

$(".mortgage_toggle").on('switchChange.bootstrapSwitch', function(event, state) {
	var $this = $(event.target);
	var propertyAddress = $this.data("address") ? $this.data("address") : '';
	if(state === true) {
		send_changed_value("txtdown_payment_percent", "20", propertyAddress);
		$this.closest("table").find(".mortgage_item").show();
	}
	else {
		send_changed_value("txtdown_payment_percent", "100", propertyAddress);
		$this.closest("table").find(".mortgage_item").hide();
	}
});

$('ul.nav li.dropdown').hover(function() {
	$(this).find('.dropdown-menu.noclick1').stop(true, true).delay(0).fadeIn(0);
}, function() {
	$(this).find('.dropdown-menu.noclick1').stop(true, true).delay(0).fadeOut(0);
});

$('.navbar .dropdown > a').click(function(){
	location.href = this.href;
});

$('.property-dropdown li a').click(function(e) {
	var $this = $(this),
		listPropertyId = [];
	$this.closest('ul').find('li a').removeClass('active');
	$this.addClass('active');
	$('ul.property-dropdown li a.active').each(function(i, obj) {
		listPropertyId.push($(obj).data('propertyId'));
	});
	
	window.location = window.location.protocol + "//" + window.location.host + "/property/compare/" + listPropertyId.join('/')
});


$(function () {

    // init for get group list - mavu 20170517
    group_list()

    //Loop through all Labels with class 'editable'.
        
    $(".editable").each(function () {
        //Reference the Label.
        var label = $(this);
 		
 		//Get property address if exist on attribute data-address
        var propertyAddress = label.data("address") ? label.data("address") : '';
 		
        //Add a TextBox next to the Label.
        label.after("<input type = 'text' style = 'display:none' data-address='"+ propertyAddress +"' />");
 
        //Reference the TextBox.
        var textbox = $(this).next();
 		
        //Set the name attribute of the TextBox.
        textbox[0].name = this.id.replace("lbl", "txt");
 
        //Assign the value of Label to TextBox.
        textbox.val(label.html());
 
        //When Label is clicked, hide Label and show TextBox.
        label.css('cursor','pointer');
        label.click(function () {
            $(this).css('display', 'none');
            $(this).next().css('display', 'inline');
            $(this).next().focus();
            $(this).next().select();
        });
 
        //When focus is lost from TextBox, hide TextBox and show Label.
        textbox.focusout(function () {
            $(this).css('display', 'none');
			var the_value = $(this).val().replace(',', '');
			var propertyAddress = $(this).data("address") ? $(this).data("address") : '';
			
            if ($(this).val() != $(this).prev().html()) {
	            if($.isNumeric(the_value) == true) {
		            //Prevent bad data
	            	if(($(this).attr('name') == "txtpurchase_price" || $(this).attr('name') == "txtrate" 
	            		|| $(this).attr('name') == "txtvaluation") && ($(this).val() <= 0)) {
	            		switch($(this).attr('name')) {
	            			case "txtrate":
	            				console.log('Mortgage rate can not be zero');
	            				break;
	            			case "txtvaluation":
	            				console.log('Estimated value not less than zero');
	            				break;
	            			default:
	            				console.log('Purchase price can not be zero');
	            		}
					}
					else {
						$(this).prev().html($(this).val());
						if ($('#projections-page').length) {
							changeProjectionsAssumptions();
						} else {
							send_changed_value($(this).attr('name'), $(this).val(), propertyAddress);
						}
					}
				}
				else {
					$(this).val($(this).prev().html());
				}
            }
            
            $(this).prev().css('display', 'inline');
        });
        
        //When enter is pressed, hide TextBox and show Label.
        textbox.keypress(function (e) {
	        var keyCode = (e.keyCode ? e.keyCode : e.which);
	        
	        if(keyCode == 13) {
		        $(this).css('display', 'none');
		        var the_value = $(this).val().replace(',', '');
		        var propertyAddress = $(this).data("address") ? $(this).data("address") : '';

	            if ($(this).val() != $(this).prev().html()) {
					//Fix toggle percent
		            if(($(this).attr('name') == "txtdown_payment_percent") && ($(this).val() == 100)) {
			            //$("#mortgage_toggle").bootstrapSwitch("state", false);
			            $(this).closest('table').find(".mortgage_toggle").bootstrapSwitch("state", false);
			        }
			        else if (($(this).attr('name') == "txtdown_payment_percent") && ($(this).val() < 100)) {
				        //$("#mortgage_toggle").bootstrapSwitch("state", true);
				        $(this).closest('table').find(".mortgage_toggle").bootstrapSwitch("state", true);
			        }
			        
			        //Fix toggle dollar
			        if ($('[name="txtpurchase_price"]').length) {
			        	var purchase_price = $('[name="txtpurchase_price"]').val().replace(",", "");
			        }
			        if ($('[name="txtdown_payment_dollar"]').length) {
			        	var down_payment_dollar = $('[name="txtdown_payment_dollar"]').val().replace(",", "");
			        }
		            if(($(this).attr('name') == "txtdown_payment_dollar") && (down_payment_dollar >= purchase_price)) {
			            //$("#mortgage_toggle").bootstrapSwitch("state", false);
			            $(this).closest('table').find(".mortgage_toggle").bootstrapSwitch("state", false);
			        }
			        else if (($(this).attr('name') == "txtdown_payment_dollar") && (down_payment_dollar < purchase_price)) {
				        //$("#mortgage_toggle").bootstrapSwitch("state", true);
				        $(this).closest('table').find(".mortgage_toggle").bootstrapSwitch("state", true);
			        }

			        
					if($.isNumeric(the_value) == true) {	
						if(($(this).attr('name') == "txtpurchase_price" || $(this).attr('name') == "txtrate" 
							|| $(this).attr('name') == "txtvaluation") && ($(this).val() <= 0)) {
							switch($(this).attr('name')) {
		            			case "txtrate":
		            				console.log('Mortgage rate can not be zero');
		            				break;
		            			case "txtvaluation":
		            				console.log('Estimated value not less than zero');
		            				break;
		            			default:
		            				console.log('Purchase price can not be zero');
		            		}
						}
						else {
							$(this).prev().html($(this).val());
							if ($('#projections-page').length) {
								changeProjectionsAssumptions();
							} else {
								send_changed_value($(this).attr('name'), $(this).val(), propertyAddress);
							}
						}
					}
	            } 
	            else {
					$(this).val($(this).prev().html());
				}
	            
	            $(this).prev().css('display', 'inline');
		    }
        });
    });
    
    $(".portfolio-button").each(function () {
	    //Reference the button.
        var button = $(this);
        
        button.click(function () {
			save_to_group($(this).attr("value"), "");
        });
	});
	
	$(".portfolio-create-button").each(function () {
	    //Reference the button.
        var button = $(this);
        
        button.click(function () {
			save_to_group("", $("#new-group").val());
        });
	});
	
	$(".group-update-button").each(function () {
	    //Reference the button.
        var button = $(this);
        
        button.click(function () {
			update_group_name($("#original-group-name").val(), $("#group-name").val());
        });
	});
	
	$("#delete-group-button").each(function () {
	    //Reference the button.
        var button = $(this);
        
        button.click(function () {
			delete_group_name($("#original-group-name").val());
        });
	});
	
	$(".generate-share-button").each(function () {
	    //Reference the button.
        var button = $(this);
        
        button.click(function () {
			save_to_group("", "My Saved Properties");
        });
	});
});

function group_list() {
    $.ajax({
        url: '/_get_group_list_ajax',
        type: 'GET',
        contentType: 'application/json',
        success: function(response) {
            response = JSON.parse(response)
            len = response.length;
            html = '<select class="form-control" id="p-group1">';
            if (len) {
                for(var i = 0; i < len; i ++ ) {
                    html += '<option value="' + response[i].portfolio_id + '">' + response[i].portfolio_name + '</option>';
                }
            }
            html += '</select>';
            $("#sel-property-group").html(html)
		    // Reload new group page
		    //console.log(response);
		},
        error: function(error) {
            console.log(error);
        }
    });
}

function update_group_name(old_name, new_name) {
	if((old_name != new_name) && (new_name != "")) {
		var form_data = {
	        'old_name': old_name,
	        'new_name': new_name
	    };
    
	    $.ajax({
	        url: '/_update_group_name_ajax',
	        type: 'POST',
	        contentType: 'application/json',
	        data: JSON.stringify(form_data),
	        success: function(response) {
				Intercom('trackEvent', 'updated-property-group', form_data);
				new_name_url = new_name.toLowerCase().replace(' ', '_');
				
				$("#update-group-button").html('Saving...');
		       
			    // Reload new group page
			    //console.log(response);
			    window.location = window.location.protocol + "//" + window.location.host + "/property/group/" + new_name_url + "/";
			},
	        error: function(error) {
	            console.log(error);
	        }
	    });
    }
}

function delete_group_name(old_name) {
	if(old_name != "My Saved Properties") {
		var form_data = {
	        'old_name': old_name
	    };
	    console.log(form_data);
	    
	    $.ajax({
	        url: '/_delete_group_name_ajax',
	        type: 'POST',
	        contentType: 'application/json',
	        data: JSON.stringify(form_data),
	        success: function(response) {
				Intercom('trackEvent', 'deleted-property-group', form_data);
				
				$("#delete-group-button").html('Deleting Group...');
		       
			    // Reload new group page
			    //console.log(response);
			    window.location = window.location.protocol + "//" + window.location.host + "/property/";
			},
	        error: function(error) {
	            console.log(error);
	        }
	    });
	}
}

function save_to_group(portfolio_id, portfolio_name) {	
	if(portfolio_id) {
		var form_data = {
	        'property': window.location.href.split('/')[4],
	        'portfolio_id': portfolio_id
	    };
    }
    else if(portfolio_name) {
		var form_data = {
	        'property': window.location.href.split('/')[4],
	        'portfolio_name': portfolio_name
	    };
    }
    else {
		var form_data = {
	        'property': window.location.href.split('/')[4]
	    };
    }
    
    $.ajax({
        url: '/_save_to_group_ajax',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(form_data),
        success: function(response) {
			Intercom('trackEvent', 'saved-property', form_data);
	        
            var results = JSON.parse(response);
            $('#saveModalButton').addClass("kv-icon-success");

            // Update group - mavu 20170515
            group_list()
			// if(portfolio_name != "My Saved Properties") {
			// 	$('#saveModal').modal('toggle');
		    // }

		    var hashids = new Hashids();
		    link_html = '<p> ' + 
							'A link to your unique calculations: ' +
							'<input type="text" class="form-control" readonly="readonly" value="sharelink">' +
						'</p>';
		    link ='https://pro.listenmoneymatters.com/share/' + hashids.encode(results['property_id']);
		    $('#shareable_button').html(link_html.replace('sharelink', link));
		},
        error: function(error) {
            console.log(error);
        }
    });
}

function send_changed_value(object_id, object_value, property) {
	var refresh_lbl = '<i rel="tooltip" id="refresh-spin" ' + 
	'class="fa fa-refresh fa-spin kv-icon kv-icon-refresh-spin ui-tooltip" ' + 
	'data-toggle="tooltip" data-placement="top" ' + 
	'data-original-title="Processing..."></i>';
    $('#lblrefresh').html(refresh_lbl);
    $(document).ready(function(){
	    $('[rel="tooltip"]').tooltip('hide');
	    $('[rel="tooltip"]').tooltip();
	});

    var form_data = {
        'property': property ? property : window.location.href.split('/')[4],
        'object_id': object_id,
        'object_value': object_value.replace(",", "")
    };
    
    $.ajax({
        url: '/_property_value_change_ajax',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(form_data),
        success: function(response) {
            results = JSON.parse(response);
            if (results.status == 'OK') {
            	update_dashboard_fields(results['data'], results['data']['address']);
            	// Update display for mortgage page
            	if ($('#mortgage-chart').length) {
            		draw_mortgage_chart(eval('['+ results.data.calc.chart_equity_value +']'), eval('['+ results.data.calc.chart_loan_balance +']'), eval('['+ results.data.calc.chart_property_value +']'));
            		updateAmortizationSchedule(results.data.calc.amortization_schedule);
            	}
            }
		},
        error: function(error) {
            console.log(error);
        }
    });
}


function update_dashboard_fields(p, property) {
	var nested_types = ['hard', 'calc', 'cost', 'mortgage'];

	for (key in p) {
		if (nested_types.indexOf(key) !== -1) {
			update_dashboard_fields(p[key], property);
		} else {
			if($('.property-'+ property).find("#lbl"+key).html() != p[key]) {
				$('.property-'+ property).find("#lbl"+key).html(p[key]);
				$('.property-'+ property).find("input[name=txt"+key+"]").val(p[key]);
				$('.property-'+ property).find("#lbl"+key).fadeTo('slow', 0.5).fadeTo('slow', 1.0);
			}
		}
	}
	
	$(document).ready(function(){
	    $('.property-'+ property).find('[rel="tooltip"]').tooltip();
	});
}


function get_projections(address, number_of_years) {
	$.ajax({
        url: '/_get_projections_ajax',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
        	address : address,
        	number_years : number_of_years
        }),
        success: function(response) {
            results = JSON.parse(response);
            if (results.status == 'OK') {
            	
            }
		},
        error: function(error) {
            console.log(error);
        }
    });
}

/**
 * Number.prototype.format(n, x)
 * 
 * @param integer n: length of decimal
 * @param integer x: length of sections
 */
Number.prototype.format = function(n, x) {
    var re = '\\d(?=(\\d{' + (x || 3) + '})+' + (n > 0 ? '\\.' : '$') + ')';
    return this.toFixed(Math.max(0, ~~n)).replace(new RegExp(re, 'g'), '$&,');
};
