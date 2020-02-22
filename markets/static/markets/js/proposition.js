$(() => {

    // Load the price history graph.
    $.ajax({
        url: prop.code+"/graph",
        success: result => $("#graph-div").html(result)
    });

    var data = new FormData();
    data.append("outcome", outcome.code);
    data.append("affirm", outcome.affirm);

    // Load the order form.
    $.ajax({
        url: prop.code+"/order",
        data: data,
        processData: false,
        success: result => $("#order-div").html(result)
    });
});