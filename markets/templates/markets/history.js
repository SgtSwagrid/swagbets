var price_data = {
    datasets: [
        {
            label: "Affirmative",
            borderColor: "green",
            fill: false,
            data: [
                {% for p in prices %}
                {
                    x: "{{p.time|date:"c"}}",
                    y: {{p.price}}
                },
                {% endfor %}
            ]
        }, {
            label: "Negative",
            borderColor: "red",
            fill: false,
            data: [
                {% for p in prices %}
                {
                    x: "{{p.time|date:"c"}}",
                    y: 100-{{p.price}}
                },
                {% endfor %}
            ]
        }
    ]
}