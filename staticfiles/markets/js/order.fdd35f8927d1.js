$(() => {

    var csrftoken = $.cookie('csrftoken');

    // Attach a CSRF token to POST requests.
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type))
                    && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // Reload the form, with a new outcome.
    function reload(outcome, affirm, data) {

        data.append("outcome", outcome);
        data.append("affirm", affirm);

        $.ajax({
            type: "POST",
            url: prop.code+"/order",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            success: result => $("#order-div").html(result)
        });
    }

    // Reload the form when a new outcome is selected.
    $("#outcomes li").each((index, element) => {
        $(element).click(() => reload(element.id, outcome.affirm, new FormData()));
    });

    // Reload the form when the affirmative/negative buttons are pressed.
    $("#btn-aff").click(() => reload(outcome.code, true, new FormData()));
    $("#btn-neg").click(() => reload(outcome.code, false, new FormData()));

    // Change bid price when price buttons are pressed.
    $("#highest-bid").click(() => {
        $("#id_price").val(outcome.bid_price);
        $("#id_price").change();
    });
    $("#latest-price").click(() => {
        $("#id_price").val(outcome.latest_price);
        $("#id_price").change();
    });
    $("#lowest-ask").click(() => {
        $("#id_price").val(outcome.ask_price);
        $("#id_price").change();
    });

    // Update total price when the bid price is changed.
    $("#id_price").change(() => {

        var price = $("#id_price").val();
        price = Math.round(price);
        if(price < 0) price = 0;
        if(price > 100) price = 100;

        var quantity = $("#id_quantity").val();
        var total = price * quantity / 100;

        $("#id_price").val(price);
        $("#id_total").val(total);
    });

    // Update total price when the quantity is changed.
    $("#id_quantity").change(() => {

        var quantity = $("#id_quantity").val();
        quantity = Math.round(quantity);
        if(quantity < 0) quantity = 0;

        var price = $("#id_price").val();
        var total = price * quantity / 100;

        $("#id_quantity").val(quantity);
        $("#id_total").val(total);
    });

    // Update quantity when the total price is changed.
    $("#id_total").change(() => {

        var total = $("#id_total").val();
        if(total < 0) total = 0;

        var price = $("#id_price").val();
        total = price == 0 ? 0 :
            Math.round(total * 100 / price) * price / 100;
        var quantity = price == 0 ? 0 :
            Math.round(total * 100 / price);

        $("#id_total").val(total);
        $("#id_quantity").val(quantity);
    });

    // Change total price when price buttons are pressed.
    $("#t5").click(() => {
        $("#id_total").val(5);
        $("#id_total").change();
    });
    $("#t10").click(() => {
        $("#id_total").val(10);
        $("#id_total").change();
    });
    $("#t20").click(() => {
        $("#id_total").val(20);
        $("#id_total").change();
    });
    $("#t50").click(() => {
        $("#id_total").val(50);
        $("#id_total").change();
    });

    // Place an order when the button is pressed.
    $("#place-order").click(event => {
        event.preventDefault();
        var data = new FormData($("#order-form")[0]);
        data.append("place-order", null);
        reload(outcome.code, outcome.affirm, data);
    });

    // Cancel an order when its cancel button is pressed.
    $("[id|='cancel']").each((index, element) => {
        $(element).click(() => {
            var data = new FormData();
            data.append("cancel-order", element.id.split("-")[1]);
            reload(outcome.code, outcome.affirm, data);
        });
    });

    //Resolve the proposition in favour of the current outcome.
    $("#resolve").click(event => {
        var data = new FormData();
        data.append("resolve", null);
        reload(outcome.code, outcome.affirm, data);
    });
});