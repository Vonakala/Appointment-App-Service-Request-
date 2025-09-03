function initMap() {
    const defaultLoc = { lat: -25.7479, lng: 28.2293 }; 
    const map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLoc,
        zoom: 12
    });

    let marker;
    const geocoder = new google.maps.Geocoder();

    function placeMarker(location) {
        if (marker) marker.setMap(null);
        marker = new google.maps.Marker({ position: location, map: map });
        document.getElementById("lat").value = location.lat();
        document.getElementById("lng").value = location.lng();

        geocoder.geocode({ location: location }, (results, status) => {
            if (status === "OK" && results[0]) {
                document.getElementById("pac-input").value = results[0].formatted_address;
            }
        });
    }

    map.addListener("click", e => placeMarker(e.latLng));

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            const posLoc = new google.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
            map.setCenter(posLoc);
            placeMarker(posLoc);
        });
    }

    const input = document.getElementById("pac-input");
    const autocomplete = new google.maps.places.Autocomplete(input);
    autocomplete.bindTo("bounds", map);
    autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        if (!place.geometry) return;
        map.setCenter(place.geometry.location);
        map.setZoom(15);
        placeMarker(place.geometry.location);
    });
}