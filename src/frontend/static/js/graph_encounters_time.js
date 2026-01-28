// Activity Over Time Chart
// DISCLAIMER: THIS CODE WAS NOT WRITTEN BY ME (ran out of time)
function createActivityChart(activityData) {
    if (!activityData || !activityData.daily_activity) {
        console.log('No activity data available');
        return;
    }

    const dailyActivity = activityData.daily_activity;
    const labels = dailyActivity.map(d => {
        const date = new Date(d.timestamp * 1000);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const counts = dailyActivity.map(d => d.count);

    const ctx = document.getElementById('activityChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Room Encounters',
                data: counts,
                borderColor: '#9b69ff',
                backgroundColor: 'rgba(155, 105, 255, 0.2)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#9b69ff',
                pointBorderColor: '#9b69ff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#9b69ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e6e1f0',
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#1a1426',
                    titleColor: '#e6e1f0',
                    bodyColor: '#e6e1f0',
                    borderColor: '#3a2f52',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: '#928ba1'
                    },
                    grid: {
                        color: '#241c33'
                    }
                },
                x: {
                    ticks: {
                        color: '#928ba1'
                    },
                    grid: {
                        color: '#241c33'
                    }
                }
            }
        }
    });
}
