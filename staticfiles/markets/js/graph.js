$(() => {

    // Reload the graph, with a new time interval.
    function reload(time) {
        $.ajax({
            type: "GET",
            url: prop.code+"/graph?time="+time,
            success: result => $("#graph-div").html(result)
        });
    }

    // Change graph interval when duration buttons are pressed.
    $("#hour").click(() => reload(60*60));
    $("#day").click(() => reload(60*60*24));
    $("#week").click(() => reload(60*60*24*7));
    $("#month").click(() => reload(60*60*24*30));
    $("#year").click(() => reload(60*60*24*365));
});