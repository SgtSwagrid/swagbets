var $ = document.getElementById.bind(document);

var price_chart = new Chart($("price-chart").getContext("2d"), {
    type: "line",
    data: price_data,
    options: {
        scales: {
            xAxes: [{
                type: "time"
            }],
            yAxes: [{
                ticks: {
                    min: 0,
                    max: 100
                }
            }]
        },
        legend: { display: false }
    }
});

class PriceTriple {

    constructor(quantity, price, total) {

        this.QUANTITY = $(quantity);
        this.PRICE = $(price);
        this.TOTAL = $(total);

        this.QUANTITY.onchange = () => {
            if (this.QUANTITY.value < 1) this.QUANTITY.value = 1;
            this.QUANTITY.value = Math.round(this.QUANTITY.value);
            this.TOTAL.value = this.QUANTITY.value * this.PRICE.value / 100;
        };

        this.PRICE.onchange = () => {
            if (this.PRICE.value < 1) this.PRICE.value = 1;
            else if (this.PRICE.value > 99) this.PRICE.value = 99;
            this.PRICE.value = Math.round(this.PRICE.value);
            this.TOTAL.value = this.QUANTITY.value * this.PRICE.value / 100;
        };

        this.TOTAL.onchange = () => {
            this.QUANTITY.value = this.TOTAL.value / this.PRICE.value * 100;
            this.QUANTITY.onchange();
        };
    }
}

new PriceTriple("id_aff-quantity", "id_aff-price", "id_aff-total");
new PriceTriple("id_neg-quantity", "id_neg-price", "id_neg-total");

$(interval).onclick = () => {
    console.log('hello world')
    price_chart.options.scales.xAxes[0].ticks = {
        min: moment().subtract(1, 'days'),
        max: moment()
    };
};