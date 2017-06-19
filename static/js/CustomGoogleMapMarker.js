
function CustomMarker(latlng, map, args, attr) {
	this.latlng = latlng;
	this.args = args;
	this.background = attr.background;
	this.score = attr.score;
	this.name = attr.name;
	this.distance = attr.distance;
	this.address = attr.address;
	this.distance = attr.distance;
	this.keyindex = attr.keyIndex;
	this.setMap(map);

}
loadGoogleApi = setInterval(function(){
	if(google && google.maps){
		clearInterval(loadGoogleApi);

		CustomMarker.prototype = new google.maps.OverlayView();

		CustomMarker.prototype.draw = function() {

			var self = this;

			var div = this.div;

			if (!div) {
                if (this.score == 0) {
                    this.score = "NA"
                }

				div = this.div = document.createElement('div');

				div.className = 'marker';

				div.style.position = 'absolute';
				div.style.cursor = 'pointer';
				div.style.width = '40px';
				div.style.height = '40px';
		        div.style.borderRadius = '50%'
		        div.style.border = '2px solid #fff'
		        div.style.color = '#fff'
				div.style.background = this.background;
		        div.style.textAlign = 'center'

		        divChild = document.createElement('div');
				divChild.innerHTML = this.score;
		        divChild.style.fontSize = '16px';
		        divChild.style.position = 'relative';
		        divChild.style.top = '9px';
		        div.appendChild(divChild);

				if (typeof(self.args.marker_id) !== 'undefined') {
					div.dataset.marker_id = self.args.marker_id;
				}
				var html = "<div class='infowindow'>";
						html+="<div class='score' style='background:"+this.background+"'>";
							html+="<div class='text'>"+this.score+"</div>";
						html+="</div>";
						html+="<div class='info'>";
							html+="<h4 class='title'>"+this.name+"</h4>";
							html+="<div>Address: "+this.address+"</div>";
							html+="<div>Distance: "+this.distance+"</div>";
						html+="</div>";
					html+="</div>";
				var infowindow = new google.maps.InfoWindow({
					content: html,
					pixelOffset: new google.maps.Size(0, -15)
				});
				var keyLocation = this.keyindex;

				google.maps.event.addDomListener(div, "click", function(event) {
					infowindow.open(this.map, self);

					$('#itemSchool tr').removeClass("active");
					$('#itemSchool tr td .td').removeClass("border-none");
					var heightTr = 70;
					$('#itemSchool tr').each(function(index,item) {

						if($(item).attr('data-key') == keyLocation) {
							$(item).addClass("active");
							$(item).prev().find('.td').addClass('border-none');
							heightTr = (heightTr * index) - heightTr;
							$('.item-list').animate({scrollTop:heightTr},300);
							return;
						}

					});

					google.maps.event.trigger(self, "click");
				});

				var panes = this.getPanes();
				panes.overlayImage.appendChild(div);
			}

			var point = this.getProjection().fromLatLngToDivPixel(this.latlng);

			if (point) {
				div.style.left = (point.x - 20) + 'px';
				div.style.top = (point.y - 25) + 'px';
			}
		};

		CustomMarker.prototype.remove = function() {
			if (this.div) {
				this.div.parentNode.removeChild(this.div);
				this.div = null;
			}
		};

		CustomMarker.prototype.getPosition = function() {
			return this.latlng;
		};

	}
}, 200);
