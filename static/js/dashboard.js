function loadStatusChart(data) {

    const canvas = document.getElementById("statusChart");

    if (!canvas) return;

    new Chart(canvas, {

        type: "doughnut",

        data: {

            labels: [
                "Healthy",
                "Monitor",
                "Plan",
                "Urgent",
                "Expired"
            ],

            datasets: [{
                data: [
                    data.healthy,
                    data.monitor,
                    data.plan,
                    data.urgent,
                    data.expired
                ],

                backgroundColor: [
                    "#22c55e",
                    "#3b82f6",
                    "#f59e0b",
                    "#f97316",
                    "#ef4444"
                ],

                borderWidth: 2
            }]
        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: {

                    position: "top"
                }

            }

        }

    });

}