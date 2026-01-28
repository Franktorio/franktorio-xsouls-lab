// Most Common Rooms Charts
// DISCLAIMER: THIS CODE WAS NOT WRITTEN BY ME (ran out of time)
function createRoomChart(canvasId, data, title) {
    if (!data || !data.top_50) {
        console.log(`No data available for ${canvasId}`);
        return;
    }
    
    const topRooms = data.top_50
    const labels = topRooms.map(r => r.room_name);
    const counts = topRooms.map(r => r.count);
    const percentages = topRooms.map(r => r.percentage);

    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Occurrences',
                data: counts,
                backgroundColor: 'rgba(155, 105, 255, 0.6)',
                borderColor: '#9b69ff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1a1426',
                    titleColor: '#e6e1f0',
                    bodyColor: '#e6e1f0',
                    borderColor: '#3a2f52',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            return `${context.parsed.x} occurrences (${percentages[idx]}%)`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#e6e1f0',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: '#928ba1',
                        font: { size: 10 }
                    },
                    grid: {
                        color: '#241c33'
                    }
                },
                y: {
                    ticks: {
                        color: '#928ba1',
                        font: { size: 10 }
                    },
                    grid: {
                        color: '#241c33'
                    }
                }
            }
        }
    });
}
