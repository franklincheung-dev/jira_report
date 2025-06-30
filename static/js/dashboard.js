/**
 * Agile Project Insights Dashboard - Main JavaScript
 */

$(document).ready(function() {
    // Global variables
    let currentSprintIndex = -1;
    let currentDashboardData = null;
    let projectDataMap = {};
    let selectedWorkloadProjects = [];
    
    // Load archived sprints when the page loads
    loadArchivedSprints();
    
    // Add team capacity calculation hint on page load
    addTeamCapacityHint();
    
    // Make sure Plotly is ready
    if (typeof Plotly === 'undefined') {
        console.error('Plotly.js is not loaded! Charts will not render correctly.');
    } else {
        console.log('Plotly.js is loaded and ready for chart rendering.');
    }
    
    /**
     * Handle file upload form submission
     */
    $('#upload-form').submit(function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const fileInput = $('#file-upload')[0];
        
        if (fileInput.files.length === 0) {
            alert('Please select a file to upload.');
            return;
        }
        
        formData.append('file', fileInput.files[0]);
        
        // Show loading indicator
        $('#loading').removeClass('d-none');
        
        // Upload file
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                $('#loading').addClass('d-none');
                
                if (response.status === 'success') {
                    // File uploaded successfully
                    populateSprintDropdown(response.sprints);
                    
                    // Enable controls
                    $('#sprint-select').prop('disabled', false);
                    $('#team-capacity').prop('disabled', false);
                    $('#generate-dashboard').prop('disabled', false);
                    $('#archive-current').prop('disabled', false);
                    
                    // Auto-fetch assignees and projects data too
                    currentSprintIndex = response.sprints.length > 0 ? 
                        response.sprints[response.sprints.length - 1].index : -1;
                    
                    // Fetch assignee and project data after upload, but check if API endpoints exist
                    try {
                        fetchAssigneeData(currentSprintIndex);
                        fetchProjectData(currentSprintIndex);
                    } catch(e) {
                        console.warn('Could not fetch assignee/project data:', e);
                        // Continue even if these fail, as they're enhancements
                    }
                } else {
                    // Error uploading file
                    alert('Error: ' + response.message);
                }
            },
            error: function() {
                $('#loading').addClass('d-none');
                alert('Error uploading file. Please try again.');
            }
        });
    });
    
    /**
     * Populate sprint dropdown with available sprints
     */
    function populateSprintDropdown(sprints) {
        const $select = $('#sprint-select');
        $select.empty();

        if (sprints && sprints.length > 0) {
            // Sort sprints intelligently - this should match backend sorting
            sprints.sort((a, b) => {
                // Helper function to extract sprint information
                function extractSprintInfo(sprintName) {
                    if (typeof sprintName !== 'string') {
                        return { type: 0, year: 0, number: 0, text: String(sprintName) };
                    }
                    
                    // Match pattern like "2025 Sprint 9"
                    const yearSprintMatch = sprintName.match(/(\d{4})\s+Sprint\s+(\d+)/);
                    if (yearSprintMatch) {
                        return { 
                            type: 1, 
                            year: parseInt(yearSprintMatch[1], 10), 
                            number: parseInt(yearSprintMatch[2], 10), 
                            text: sprintName 
                        };
                    }
                    
                    // Match pattern like "Sprint 9"
                    const sprintMatch = sprintName.match(/Sprint\s+(\d+)/);
                    if (sprintMatch) {
                        return { 
                            type: 2, 
                            year: 0, 
                            number: parseInt(sprintMatch[1], 10), 
                            text: sprintName 
                        };
                    }
                    
                    // Default: alphabetical sort
                    return { type: 3, year: 0, number: 0, text: sprintName };
                }
                
                const nameA = a.name || a.sprint_name || '';
                const nameB = b.name || b.sprint_name || '';
                const infoA = extractSprintInfo(nameA);
                const infoB = extractSprintInfo(nameB);
                
                // Sort by type first
                if (infoA.type !== infoB.type) {
                    return infoA.type - infoB.type;
                }
                
                // If same type, sort by year (for type 1)
                if (infoA.type === 1 && infoA.year !== infoB.year) {
                    return infoA.year - infoB.year;
                }
                
                // If same year or not year-based, sort by sprint number
                if ((infoA.type === 1 || infoA.type === 2) && infoA.number !== infoB.number) {
                    return infoA.number - infoB.number;
                }
                
                // Default to text comparison
                return infoA.text.localeCompare(infoB.text);
            });
            
            // Update indices after sorting if they are present
            sprints.forEach((sprint, i) => {
                if (sprint.index !== undefined) {
                    sprint.sortedIndex = i;
                }
            });

            sprints.forEach(function(sprint, idx) {
                // Support both current and archived sprint objects
                const sprintName = sprint.name || sprint.sprint_name || `Sprint ${idx + 1}`;
                let sprintText = sprintName;
                
                // Add details (total points, completion) if available
                if (sprint.total_points !== undefined && sprint.total_points > 0) {
                    const completionPercentage = sprint.total_points > 0 ? 
                        Math.round((sprint.completed_points / sprint.total_points) * 100) : 0;
                    sprintText += ` (${sprint.completed_points}/${sprint.total_points} hrs, ${completionPercentage}%)`;
                }
                
                const value = sprint.index !== undefined ? sprint.index : (sprint.id || idx);
                $select.append(`<option value="${value}">${sprintText}</option>`);
            });

            // Select the most recent sprint by default
            const lastSprint = sprints[sprints.length - 1];
            if (lastSprint && lastSprint.index !== undefined) {
                $select.val(lastSprint.index);
                currentSprintIndex = lastSprint.index;
            }
        } else {
            $select.append('<option value="">No sprints available</option>');
        }
    }
    
    // Fetch issue types and billable configuration functions removed as requested
    
    /**
     * Handle sprint selection change
     */
    $('#sprint-select').change(function() {
        currentSprintIndex = $(this).val();
        // No need to regenerate the dashboard here - the user will click the Generate Dashboard button
    });
    
    /**
     * Add a helpful capacity calculation hint
     */
    function addTeamCapacityHint() {
        // Get the capacity input group
        const $capacityGroup = $('#team-capacity').closest('.form-group');
        
        // Check if the hint already exists to avoid duplicates
        if ($capacityGroup.find('.capacity-hint').length === 0) {
            // Calculate a simple example (7 people × 8 hours × 5 days = 280 hours)
            $capacityGroup.append('<small class="text-muted d-block mt-1 capacity-hint"><i class="fas fa-calculator"></i> Example: 7 people × 8 hours × 5 days = 280 hours</small>');
        }
    }
    
    /**
     * Generate dashboard based on selected sprint
     */
    $('#generate-dashboard').click(function() {
        // Get selected sprint index
        const sprintIndex = $('#sprint-select').val();
        currentSprintIndex = sprintIndex;
        
        // Get team capacity
        const teamCapacity = parseFloat($('#team-capacity').val()) || 0;
        
        // Hide upload prompt
        $('#upload-prompt').addClass('d-none');
        
        // Show loading indicator
        $('#loading').removeClass('d-none');
        
        // Validate chart containers
        validateChartContainers();
        
        // Validate chart containers before making request
        validateChartContainers();
        
        // Generate dashboard
        $.ajax({
            url: '/get-dashboard',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                sprint_index: sprintIndex,
                team_capacity: teamCapacity
            }),
            success: function(response) {
                $('#loading').addClass('d-none');
                
                if (response.status === 'success') {
                    // Show dashboard container
                    $('#dashboard-container').removeClass('d-none');
                    
                    // Store dashboard data for later use
                    currentDashboardData = response.dashboard;
                    
                    // Log dashboard data to inspect structure
                    console.log('Dashboard data received:', response.dashboard);
                    
                    // Update dashboard with data
                    updateDashboard(response.dashboard);
                    
                    // Fetch assignee and project data
                    fetchAssigneeData(sprintIndex);
                    fetchProjectData(sprintIndex);
                } else {
                    // Error generating dashboard
                    console.error('Error generating dashboard:', response.message);
                    alert('Error: ' + response.message);
                }
            },
            error: function(xhr, status, error) {
                $('#loading').addClass('d-none');
                console.error('AJAX error:', status, error);
                alert('Error generating dashboard. Please try again.');
            }
        });
    });
    
    /**
     * Validate chart containers before rendering
     */
    function validateChartContainers() {
        const chartIds = [
            // Main dashboard charts
            'completion-chart', 'velocity-chart', 'billable-chart', 'capacity-chart',
            // Assignee detail charts
            'assignee-completion-chart', 'assignee-category-chart', 'assignee-occupancy-chart',
            // Project detail charts
            'project-completion-chart', 'project-resource-allocation-chart'
        ];
        
        chartIds.forEach(id => {
            const container = $(`#${id}`);
            if (container.length === 0) {
                console.error(`Chart container #${id} not found in HTML!`);
            } else {
                // Check if container has size
                const width = container.width();
                const height = container.height();
                
                if (width === 0 || height === 0) {
                    console.warn(`Chart container #${id} has zero width or height. Width: ${width}px, Height: ${height}px`);
                    // Try to ensure container has size
                    container.css({
                        'min-height': '250px',
                        'width': '100%',
                        'display': 'block',
                        'visibility': 'visible'
                    });
                } else {
                    console.log(`Chart container #${id} size: Width: ${width}px, Height: ${height}px`);
                }
            }
        });
    }
    
    /**
     * Fetch assignee data from the server
     */
    function fetchAssigneeData(sprintIndex) {
        console.log('Fetching assignee data for sprint index:', sprintIndex);
        
        $.ajax({
            url: '/get-assignee-data',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                sprint_index: sprintIndex
            }),
            success: function(response) {
                console.log('Received assignee data:', response);
                if (response.status === 'success') {
                    // Render assignee filter bubbles
                    renderAssigneeBubbles(response.assignees);
                } else {
                    console.error('Error in assignee data response:', response.message || 'Unknown error');
                }
            },
            error: function(xhr, status, error) {
                console.error('Error fetching assignee data:', status, error);
            }
        });
    }
    
    /**
     * Fetch project data from the server
     */
    function fetchProjectData(sprintIndex) {
        console.log('Fetching project data for sprint index:', sprintIndex);
        
        $.ajax({
            url: '/get-project-data',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                sprint_index: sprintIndex
            }),
            success: function(response) {
                console.log('Received project data:', response);
                if (response.status === 'success') {
                    // Render project filter bubbles
                    renderProjectBubbles(response.projects);

                    // Store project data for workload table
                    projectDataMap = {};
                    response.projects.forEach(p => {
                        projectDataMap[p.name] = p;
                    });

                    // Populate project bubbles for workload table
                    populateWorkloadProjectBubbles(response.projects);
                } else {
                    console.error('Error in project data response:', response.message || 'Unknown error');
                }
            },
            error: function(xhr, status, error) {
                console.error('Error fetching project data:', status, error);
            }
        });
    }
    
    /**
     * Update dashboard with data received from server
     * @param {Object} dashboard - Dashboard data from server
     */
    function updateDashboard(dashboard) {
        if (!dashboard) {
            console.error('No dashboard data provided');
            return;
        }
        
        console.log('Updating dashboard with data:', dashboard);
        // Debug logging to check keys
        console.log('Dashboard contains blockers:', dashboard.hasOwnProperty('blockers'));
        console.log('Dashboard contains projected_capacity:', dashboard.hasOwnProperty('projected_capacity'));
        if (dashboard.blockers) {
            console.log('Blockers data:', dashboard.blockers);
        }
        if (dashboard.projected_capacity) {
            console.log('Projected capacity data:', dashboard.projected_capacity);
        }
        
        // Ensure Plotly is available
        ensurePlotly();
        
        // Reset any containers that might have been overwritten
        $('#blockers-list').empty();
        $('#capacity-forecast').empty();


        // Set the sprint name
        $('#sprint-name').text(dashboard.metrics.sprint_name || 'Unknown Sprint');
        $('#sprint-status').text(dashboard.metrics.sprint_status || 'Unknown');
        
        // Update basic metrics
        if (dashboard.metrics) {
            $('#metric-total-issues').text(dashboard.metrics.total_issues || 0);
            $('#metric-total-points').text(dashboard.metrics.total_points !== undefined ? dashboard.metrics.total_points.toFixed(1) : '0.0');
            $('#metric-completed-points').text(dashboard.metrics.completed_points !== undefined ? dashboard.metrics.completed_points.toFixed(1) : '0.0');
            $('#metric-completion-percentage').text(dashboard.metrics.completion_percentage !== undefined ? Math.round(dashboard.metrics.completion_percentage) + '%' : '0%');
        } else {
            console.warn('No metrics data found in dashboard object');
            // Set default values
            $('#metric-total-issues').text('0');
            $('#metric-total-points').text('0.0');
            $('#metric-completed-points').text('0.0');
            $('#metric-completion-percentage').text('0%');
        }
        
        // Update sprint info if available
        if (dashboard.current_sprint_details) {
            const sprintDetails = dashboard.current_sprint_details;
            $('#current-sprint-name').text(sprintDetails.name || 'Unknown Sprint');
            
            // Calculate dates if available
            if (sprintDetails.start_date && sprintDetails.end_date) {
                $('#sprint-date-range').text(`${sprintDetails.start_date} to ${sprintDetails.end_date}`);
            }
        }
        
        // Update charts from the dashboard data
        // Ensure chart containers have proper dimensions
        validateChartContainers();
        
        // Completion donut chart
        if (dashboard.completion_chart) {
            try {
                // Parse the JSON safely
                let chartData;
                try {
                    chartData = typeof dashboard.completion_chart === 'string' ? 
                        JSON.parse(dashboard.completion_chart) : dashboard.completion_chart;
                } catch (parseError) {
                    console.error('Error parsing completion chart JSON:', parseError);
                    return;
                }
                
                Plotly.newPlot('completion-chart', chartData.data || chartData, chartData.layout || {}, {responsive: true});
            } catch (error) {
                console.error('Error rendering completion chart:', error);
            }
        }
        
        // Category breakdown chart
        if (dashboard.billable_chart) {
            try {
                // Parse the JSON safely
                let chartData;
                try {
                    chartData = typeof dashboard.billable_chart === 'string' ? 
                        JSON.parse(dashboard.billable_chart) : dashboard.billable_chart;
                } catch (parseError) {
                    console.error('Error parsing billable chart JSON:', parseError);
                    return;
                }
                
                Plotly.newPlot('billable-chart', chartData.data || chartData, chartData.layout || {}, {responsive: true});
            } catch (error) {
                console.error('Error rendering billable chart:', error);
            }
        }
        
        // Team capacity chart
        if (dashboard.capacity_chart) {
            try {
                // Parse the JSON safely
                let chartData;
                try {
                    chartData = typeof dashboard.capacity_chart === 'string' ? 
                        JSON.parse(dashboard.capacity_chart) : dashboard.capacity_chart;
                } catch (parseError) {
                    console.error('Error parsing capacity chart JSON:', parseError);
                    return;
                }
                
                Plotly.newPlot('capacity-chart', chartData.data || chartData, chartData.layout || {}, {responsive: true});
            } catch (error) {
                console.error('Error rendering capacity chart:', error);
            }
        }
        
        // Velocity trend chart
        if (dashboard.velocity_chart) {
            try {
                // Parse the JSON safely
                let chartData;
                try {
                    chartData = typeof dashboard.velocity_chart === 'string' ? 
                        JSON.parse(dashboard.velocity_chart) : dashboard.velocity_chart;
                } catch (parseError) {
                    console.error('Error parsing velocity chart JSON:', parseError);
                    return;
                }
                
                Plotly.newPlot('velocity-chart', chartData.data || chartData, chartData.layout || {}, {responsive: true});
            } catch (error) {
                console.error('Error rendering velocity chart:', error);
            }
        }
        
        // Update blockers list if available
        if (dashboard.metrics.blockers) {
            console.log('Found blockers in dashboard data:', dashboard.blockers);
            updateBlockersList(dashboard.metrics.blockers);
        } else {
            console.warn('No blockers found in dashboard data');
            $('#blockers-list').html('<p class="text-muted">No blockers or at-risk items found for this sprint.</p>');
        }
        
        // Update capacity forecast if available
        if (dashboard.projected_capacity) {
            console.log('Found projected capacity in dashboard data:', dashboard.projected_capacity);
            updateCapacityForecast(dashboard.projected_capacity);
        } else {
            console.warn('No projected capacity found in dashboard data');
            $('#capacity-forecast').html('<p class="text-muted">No capacity forecast data available.</p>');
        }
        
        // Show the dashboard container if it's hidden
        $('#dashboard-container').removeClass('d-none');
    }
    
    /**
     * Update the blockers list with data from the server
     * @param {Object} blockerData - Object containing blocker lists
     */
    /**
     * Update the blockers list with data from the server
     * @param {Object} blockerData - Object containing blocker lists
     */
    function updateBlockersList(blockerData) {
        const container = $('#blockers-list');
        if (container.length === 0) {
            console.error('Blockers list container (#blockers-list) not found in HTML!');
            return;
        }

        console.log('Updating blockers list with data:', blockerData);
        container.empty();

        // Ensure we have valid data
        if (!blockerData) {
            container.html('<p class="text-muted">No blockers data available.</p>');
            return;
        }

        // Handle both old and new data formats
        let generalBlockers = blockerData.blockers || blockerData;

        // Add summary counts at the top
        const totalBlockers = generalBlockers.length;
        const overdueBlockers = generalBlockers.filter(b => b.blocker_type === 'overdue').length;
        const incompleteBlockers = generalBlockers.filter(b => b.blocker_type === 'incomplete').length;

        const summaryHtml = `
            <div class="blocker-summary mb-3">
                <span class="badge bg-secondary me-2">Total: ${totalBlockers}</span>
                <span class="badge bg-danger me-2">Overdue: ${overdueBlockers}</span>
                <span class="badge bg-warning text-dark">Incomplete: ${incompleteBlockers}</span>
            </div>
        `;

        container.append(summaryHtml);

        // Create the blockers table
        if (!generalBlockers || generalBlockers.length === 0) {
            container.append('<p class="text-muted">No blockers or at-risk items found for this sprint.</p>');
            return;
        }

        const table = $(`
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Summary</th>
                        <th>Assignee</th>
                        <th>Status</th>
                        <th>Due Date</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `);

        const tbody = table.find('tbody');

        generalBlockers.forEach(blocker => {
            const rowClass = blocker.blocker_type === 'overdue' ? 'table-danger' : 'table-warning';
            const row = $(`<tr class="${rowClass}"></tr>`);

            const dueDate = blocker['Due date'] ? new Date(blocker['Due date']).toLocaleDateString() : 'Not set';

            row.append(`
                <td><a href="${blocker.issue_url || `https://benoveltyv3.atlassian.net/browse/${blocker['Issue key']}`}" target="_blank">${blocker['Issue key']}</a></td>
                <td>${blocker['Summary']}</td>
                <td>${blocker['Assignee'] || 'Unassigned'}</td>
                <td>${blocker['Status']}</td>
                <td>${dueDate}</td>
            `);

            tbody.append(row);
        });

        container.append(table);
    }
    
    /**
     * Update the capacity forecast section with projected capacity data
     * @param {Object} projectedCapacity - Projected capacity data
     */
    function updateCapacityForecast(projectedCapacity) {
        const container = $('#capacity-forecast');
        if (container.length === 0) {
            console.error('Capacity forecast container (#capacity-forecast) not found in HTML!');
            return;
        }
        
        console.log('Updating capacity forecast with data:', projectedCapacity);
        container.empty();
        
        if (!projectedCapacity) {
            container.append('<p class="text-muted">No forecast data available.</p>');
            return;
        }
        
        // Get data for the current, next sprint and sprint after next
        const currentSprint = projectedCapacity.current_sprint || {};
        const nextSprint = projectedCapacity.next_sprint || {};
        const nextNextSprint = projectedCapacity.next_next_sprint || {};
        const historical = projectedCapacity.historical || {};
        
        // Create a forecast panel for the cards
        // Use responsive classes for mobile
        const forecastPanel = $('<div class="row forecast-row gx-2 gy-2"></div>');
        
        // Function to create a forecast card
        function createForecastCard(sprint, title, badgeText, badgeClass) {
            if (!sprint || sprint.forecast_hours === undefined) return null;
            
            // Format category breakdown
            let categoryHtml = '';
            if (sprint.category_breakdown) {
                categoryHtml = '<div class="category-breakdown mt-3">';
                categoryHtml += '<h6 class="text-muted mb-2">Category Breakdown</h6>';
                categoryHtml += '<div class="row">';
                
                for (const [category, hours] of Object.entries(sprint.category_breakdown)) {
                    const categoryClass = category.toLowerCase();
                    categoryHtml += `
                        <div class="col-6 mb-2">
                            <span class="badge category-${categoryClass}">${category}</span>
                            <span class="ms-2">${hours.toFixed(1)} hrs</span>
                        </div>
                    `;
                }
                
                categoryHtml += '</div></div>';
            }
            
            // Allocation metrics
            let allocationHtml = '';
            if (sprint.unallocated_hours !== undefined) {
                const allocatedPct = sprint.allocated_hours && sprint.forecast_hours ? 
                    Math.round((sprint.allocated_hours / sprint.forecast_hours) * 100) : 0;
                
                allocationHtml = `
                    <div class="allocation-metrics mt-3">
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Allocated</span>
                            <span>${sprint.allocated_hours ? sprint.allocated_hours.toFixed(1) : '0.0'} hrs (${allocatedPct}%)</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Unallocated</span>
                            <span>${sprint.unallocated_hours.toFixed(1)} hrs (${sprint.remaining_percentage}%)</span>
                        </div>
                    </div>
                `;
            }
            
            return $(
                `<div class="col-12 col-sm-6 col-lg-4 mb-3 d-flex align-items-stretch">
                    <div class="card h-100 w-100">
                        <div class="card-header bg-light d-flex justify-content-between align-items-center">
                            <h6 class="m-0">${title}</h6>
                            <span class="badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="card-body">
                            <div class="text-center mb-3">
                                <h3>${sprint.forecast_hours.toFixed(1)} hours</h3>
                                <p class="text-muted mb-0">${sprint.sprint_name}</p>
                            </div>
                            ${categoryHtml}
                            ${allocationHtml}
                        </div>
                    </div>
                </div>`
            );
        }
        
        // Add current sprint forecast
        const currentSprintCard = createForecastCard(
            currentSprint, 
            "Current Sprint", 
            "Current", 
            "bg-success"
        );
        if (currentSprintCard) {
            forecastPanel.append(currentSprintCard);
        }
        
        // Add next sprint forecast
        const nextSprintCard = createForecastCard(
            nextSprint, 
            "Next Sprint Forecast", 
            "Expected", 
            "bg-primary"
        );
        if (nextSprintCard) {
            forecastPanel.append(nextSprintCard);
        }
        
        // Add sprint after next forecast
        const nextNextSprintCard = createForecastCard(
            nextNextSprint, 
            "Sprint After Next", 
            "Projected", 
            "bg-info"
        );
        if (nextNextSprintCard) {
            forecastPanel.append(nextNextSprintCard);
        }
        
        container.append(forecastPanel);
        
        // Add historical metrics and context
        if (historical) {
            const historicalSection = $(`
                <div class="historical-metrics mt-4">
                    <h6><i class="fas fa-history"></i> Historical Context</h6>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-title">Average Velocity</div>
                                <div class="metric-value">${historical.avg_velocity ? historical.avg_velocity.toFixed(1) : '0.0'} hrs</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-title">Latest Moving Avg</div>
                                <div class="metric-value">${historical.latest_moving_avg ? historical.latest_moving_avg.toFixed(1) : '0.0'} hrs</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="metric-card">
                                <div class="metric-title">Historical Utilization</div>
                                <div class="metric-value">${currentSprint && currentSprint.historical_utilization ? currentSprint.historical_utilization.toFixed(1) : '0.0'}%</div>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            container.append(historicalSection);
        }
        
        // Add data quality notes if available
        if (historical && historical.data_quality_warning) {
            container.append(`<div class="forecast-notes mt-3"><p class="text-warning"><i class="fas fa-exclamation-triangle"></i> ${historical.data_quality_warning}</p></div>`);
        }
        
        // Add forecast notes if available
        if (projectedCapacity.notes) {
            container.append(`<div class="forecast-notes mt-3"><p class="text-muted"><i class="fas fa-info-circle"></i> ${projectedCapacity.notes}</p></div>`);
        }
    }
    
    /**
     * Render assignee filter bubbles
     */
    function renderAssigneeBubbles(assignees) {
        const container = $('#assignee-bubbles');
        container.empty();
        
        if (!assignees || assignees.length === 0) {
            container.append('<p class="text-muted">No assignee data available</p>');
            return;
        }
        
        // Sort assignees by workload (total points) in descending order
        assignees.sort((a, b) => b.total_points - a.total_points);
        
        // Create a bubble for each assignee
        assignees.forEach(assignee => {
            // Get workload class based on total points
            const workloadClass = getWorkloadClass(assignee.total_points);
            
            // Create initials for the avatar
            const initials = getInitials(assignee.name);
            
            const bubble = $(`
                <div class="filter-bubble assignee-bubble" data-assignee="${assignee.name}">
                    <div class="avatar">${initials}</div>
                    <span>${assignee.name}</span>
                    <span class="ms-2 workload-indicator ${workloadClass}"></span>
                </div>
            `);
            
            // Store assignee data in the bubble for later use
            bubble.data('assigneeData', assignee);
            
            // Add click event to show assignee details
            bubble.click(function() {
                // Remove active class from all assignee bubbles
                $('.assignee-bubble').removeClass('active');
                // Add active class to this bubble
                $(this).addClass('active');
                
                // Show assignee details
                showAssigneeDetails($(this).data('assigneeData'));
                
                // Hide project details if visible
                $('#project-detail-view').addClass('d-none');
                $('.project-bubble').removeClass('active');
            });
            
            container.append(bubble);
        });
    }
    
    /**
     * Render project filter bubbles
     */
function renderProjectBubbles(projects) {
        const container = $('#project-bubbles');
        container.empty();
        
        if (!projects || projects.length === 0) {
            container.append('<p class="text-muted">No project data available</p>');
            return;
        }
        
        // Sort projects by total points in descending order
        projects.sort((a, b) => b.total_points - a.total_points);
        
        // Create a bubble for each project
        projects.forEach(project => {
            // Calculate completion class
            const completionClass = getCompletionClass(project.completion_percentage);
            
            const bubble = $(`
                <div class="filter-bubble project-bubble ${completionClass}" data-project="${project.name}">
                    <i class="fas fa-project-diagram me-2"></i>
                    <span>${project.name}</span>
                </div>
            `);
            
            // Store project data in the bubble for later use
            bubble.data('projectData', project);
            
            // Add click event to show project details
            bubble.click(function() {
                // Remove active class from all project bubbles
                $('.project-bubble').removeClass('active');
                // Add active class to this bubble
                $(this).addClass('active');
                
                // Show project details
                showProjectDetails($(this).data('projectData'));
                
                // Hide assignee details if visible
                $('#assignee-detail-view').addClass('d-none');
                $('.assignee-bubble').removeClass('active');
            });
            
            container.append(bubble);
        });
    }

    /**
     * Populate the multi-select dropdown for workload table
     */
    function populateWorkloadProjectBubbles(projects) {
        const container = $('#workload-project-bubbles');
        if (container.length === 0) return;

        container.empty();
        selectedWorkloadProjects = [];
        projects.forEach(project => {
            const bubble = $(
                `<div class="filter-bubble workload-project-bubble" data-project="${project.name}">${project.name}</div>`
            );

            bubble.click(function() {
                $(this).toggleClass('active');
                const name = $(this).data('project');
                if ($(this).hasClass('active')) {
                    if (!selectedWorkloadProjects.includes(name)) {
                        selectedWorkloadProjects.push(name);
                    }
                } else {
                    selectedWorkloadProjects = selectedWorkloadProjects.filter(p => p !== name);
                }
                updateWorkloadTable();
            });

            container.append(bubble);
        });

        updateWorkloadTable();
    }

    /**
     * Update workload table based on selected projects
     */
    function updateWorkloadTable() {
        const selected = selectedWorkloadProjects;
        const table = $('#workload-table');
        if (table.length === 0) return;

        const thead = table.find('thead');
        const tbody = table.find('tbody');

        if (!selected || selected.length === 0) {
            thead.empty();
            tbody.empty();
            return;
        }

        // Collect all assignees
        const assigneeSet = new Set();
        selected.forEach(p => {
            const dist = projectDataMap[p]?.assignee_distribution || {};
            Object.keys(dist).forEach(a => assigneeSet.add(a));
        });
        const assignees = Array.from(assigneeSet).sort();

        // Find max hours for color scaling
        let maxHours = 0;
        selected.forEach(p => {
            const dist = projectDataMap[p]?.assignee_distribution || {};
            assignees.forEach(a => {
                const hrs = dist[a] || 0;
                if (hrs > maxHours) maxHours = hrs;
            });
        });

        // Build header
        let headerHtml = '<tr><th>Assignee</th>';
        selected.forEach(p => {
            headerHtml += `<th>${p}</th>`;
        });
        headerHtml += '</tr>';
        thead.html(headerHtml);

        // Build body
        tbody.empty();

        const columnTotals = {};
        selected.forEach(p => { columnTotals[p] = 0; });

        assignees.forEach(a => {
            let rowHtml = `<tr><td>${a}</td>`;
            selected.forEach(p => {
                const hrs = projectDataMap[p]?.assignee_distribution[a] || 0;
                columnTotals[p] += hrs;
                let pct = maxHours > 0 ? hrs / maxHours : 0;
                let cls = '';
                if (pct > 0.66) cls = 'table-danger';
                else if (pct > 0.33) cls = 'table-warning';
                else if (pct > 0) cls = 'table-success';
                rowHtml += `<td class="${cls}">${hrs.toFixed(1)}</td>`;
            });
            rowHtml += '</tr>';
            tbody.append(rowHtml);
        });

        // Totals row
        let totalRowHtml = '<tr><th>Total</th>';
        selected.forEach(p => {
            totalRowHtml += `<th>${columnTotals[p].toFixed(1)}</th>`;
        });
        totalRowHtml += '</tr>';
        tbody.append(totalRowHtml);
    }
    
    /**
     * Show assignee details
     */
    function showAssigneeDetails(assignee) {
        if (!assignee) {
            console.warn('No assignee data provided');
            return;
        }
        
        console.log('Showing details for assignee:', assignee);
        
        // Set assignee name
        $('#assignee-detail-name').html(`<i class="fas fa-user"></i> ${assignee.name || 'Unknown'}`);
        
        // Show assignee detail view
        $('#assignee-detail-view').removeClass('d-none');
        $('#selected-assignee-info').removeClass('d-none');
        
        // Before creating charts, ensure containers are visible and sized
        $('#assignee-completion-chart, #assignee-category-chart, #assignee-occupancy-chart').css({
            'min-height': '250px',
            'width': '100%',
            'display': 'block',
            'visibility': 'visible'
        });

        // Create occupancy rate donut chart
        const standardSprintHours = 40; // Standard hours per sprint
        const actualHours = assignee.total_points || 0;
        const occupancyPercentage = Math.min((actualHours / standardSprintHours) * 100, 100);
        
        const occupancyChartData = {
            values: [occupancyPercentage, Math.max(0, 100 - occupancyPercentage)],
            labels: ['Occupied', 'Available'],
            type: 'pie',
            hole: 0.7,
            marker: {
                colors: ['#4CAF50', '#f5f5f5']
            },
            textinfo: 'none',
            hoverinfo: 'label+percent',
            showlegend: false
        };

        const occupancyLayout = {
            title: {
                text: 'Sprint Occupancy Rate',
                y: 0.95
            },
            annotations: [{
                font: {
                    size: 20
                },
                showarrow: false,
                text: `${Math.round(occupancyPercentage)}%`,
                x: 0.5,
                y: 0.5
            }],
            height: 300,
            margin: { t: 40, b: 0, l: 0, r: 0 }
        };

        Plotly.newPlot('assignee-occupancy-chart', [occupancyChartData], occupancyLayout, { responsive: true });

        // Small delay to ensure DOM is updated before chart creation
        setTimeout(() => {
            // Create completion chart
            createAssigneeCompletionChart(assignee);
            
            // Create category breakdown chart
            createAssigneeCategoryChart(assignee);
            
            // Render blockers list
            renderAssigneeBlockersList(assignee);
        }, 50);
    }
    
    /**
     * Show project details
     */
    function showProjectDetails(project) {
        if (!project) {
            console.error('No project data provided to showProjectDetails');
            return;
        }
        
        console.log('Showing details for project:', project);
        
        // Set project name
        $('#project-detail-name').html(`<i class="fas fa-project-diagram"></i> ${project.name || 'Unknown'}`);
        
        // Update the dedicated area with total hours
        const totalHours = project.total_points || 0;
        $('#project-hours-value').text(totalHours.toFixed(1));
        
        // Show project detail view
        $('#project-detail-view').removeClass('d-none');
        $('#selected-project-info').removeClass('d-none');
        
        // Before creating charts, ensure containers are visible and sized
        $('#project-completion-chart, #project-resource-allocation-chart').css({
            'min-height': '250px',
            'width': '100%',
            'display': 'block',
            'visibility': 'visible'
        });
        
        // Small delay to ensure DOM is updated before chart creation
        setTimeout(() => {
            // Create completion chart
            createProjectCompletionChart(project);
            
            // Create resource allocation chart
            createProjectResourceAllocationChart(project);
            
            // Render team members
            renderProjectTeamMembers(project);
            
            // Render project blockers list
            renderProjectBlockersList(project);
        }, 50);
    }
    
    /**
     * Create assignee completion chart
     */
    function createAssigneeCompletionChart(assignee) {
        // First ensure the container exists and has size
        const container = $('#assignee-completion-chart');
        if (container.length === 0) {
            console.error('Assignee completion chart container not found!');
            return;
        }
        
        // Make sure Plotly is available
        if (!ensurePlotly()) return;
        
        // Ensure the container has proper dimensions
        if (container.width() === 0 || container.height() === 0) {
            container.css({
                'min-height': '250px',
                'width': '100%',
                'display': 'block'
            });
        }
        
        // Calculate proper values
        const completed = assignee.completed_points || 0;
        const total = assignee.total_points || 0;
        const remaining = total > completed ? total - completed : 0;
        const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
        
        const data = [{
            values: [completed, remaining],
            labels: ['Completed', 'Remaining'],
            type: 'pie',
            hole: 0.7,
            marker: {
                colors: ['#10b981', '#e2e8f0']
            },
            textinfo: 'percent',
            hoverinfo: 'label+value'
        }];
        
        const layout = {
            title: 'Completion Rate',
            height: 300,
            margin: {
                l: 0,
                r: 0,
                b: 30,
                t: 30,
                pad: 0
            },
            annotations: [{
                text: `${percentage}%`,
                font: {
                    size: 24,
                    color: '#334155'
                },
                showarrow: false,
                x: 0.5,
                y: 0.5
            }]
        };
        
        try {
            Plotly.newPlot('assignee-completion-chart', data, layout, {responsive: true});
            console.log('Assignee completion chart created successfully');
        } catch (error) {
            console.error('Error rendering assignee completion chart:', error);
            container.html('<div class="alert alert-danger">Failed to render chart. See console for details.</div>');
        }
    }
    
    /**
     * Create assignee category chart
     */
    function createAssigneeCategoryChart(assignee) {
        // First ensure the container exists and has size
        const container = $('#assignee-category-chart');
        if (container.length === 0) {
            console.error('Assignee category chart container not found!');
            return;
        }
        
        // Make sure Plotly is available
        if (!ensurePlotly()) return;
        
        // Ensure the container has proper dimensions
        if (container.width() === 0 || container.height() === 0) {
            container.css({
                'min-height': '250px',
                'width': '100%',
                'display': 'block'
            });
        }
        
        // Transform category breakdown to arrays for the chart
        const categoryBreakdown = assignee.category_breakdown || {};
        if (Object.keys(categoryBreakdown).length === 0) {
            container.html('<div class="alert alert-info">No category data available for this assignee.</div>');
            return;
        }
        
        const categories = Object.keys(categoryBreakdown);
        const values = categories.map(cat => categoryBreakdown[cat]);
        
        const categoryColors = {
            'Billable': '#3b82f6',
            'Product': '#8b5cf6',
            'Internal': '#f59e0b',
            'Other': '#94a3b8'
        };
        
        const colors = categories.map(cat => categoryColors[cat] || '#94a3b8');
        
        const data = [{
            x: categories,
            y: values,
            type: 'bar',
            marker: {
                color: colors
            },
            text: values.map(v => v.toFixed(1) + ' hrs'),
            textposition: 'auto'
        }];
        
        const layout = {
            title: 'Work Category Distribution',
            height: 300,
            margin: {
                l: 50,
                r: 20,
                b: 60,
                t: 30
            },
            yaxis: {
                title: 'Hours'
            },
            barmode: 'group'
        };
        
        try {
            Plotly.newPlot('assignee-category-chart', data, layout, {responsive: true});
            console.log('Assignee category chart created successfully');
        } catch (error) {
            console.error('Error rendering assignee category chart:', error);
            container.html('<div class="alert alert-danger">Failed to render chart. See console for details.</div>');
        }
    }
    
    /**
     * Render assignee blockers list
     */
    /**
     * Render assignee-specific blockers list
     * @param {Object} assignee - Assignee data including blockers
     */
    function renderAssigneeBlockersList(assignee) {
        const container = $('#assignee-blockers-list');
        container.empty();
        
        if (!assignee.blockers || assignee.blockers.length === 0) {
            container.append('<p class="text-muted">No blockers found</p>');
            return;
        }
        
        // Add summary counts at the top
        const totalBlockers = assignee.blockers.length;
        const overdueBlockers = assignee.blockers.filter(b => (b.blocker_type || b.blockerType) === 'overdue').length;
        const incompleteBlockers = totalBlockers - overdueBlockers;

        const summaryHtml = `
            <div class="blocker-summary mb-3">
                <span class="badge bg-secondary me-2">Total: ${totalBlockers}</span>
                <span class="badge bg-danger me-2">Overdue: ${overdueBlockers}</span>
                <span class="badge bg-warning text-dark">Incomplete: ${incompleteBlockers}</span>
            </div>
        `;

        container.append(summaryHtml);

        const table = $(`
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Summary</th>
                        <th>Status</th>
                        <th>Due Date</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `);

        const tbody = table.find('tbody');

        assignee.blockers.forEach(blocker => {
            // Extract blocker type or default to 'incomplete'
            const blockerType = blocker['blocker_type'] || blocker['blockerType'] || 'incomplete';
            const rowClass = blockerType === 'overdue' ? 'table-danger' : 'table-warning';
            const row = $(`<tr class="${rowClass}"></tr>`);

            // Format the due date
            let dueDate = 'Not set';
            const dueDateValue = blocker['Due date'] || blocker['due_date'] || blocker['dueDate'];
            if (dueDateValue) {
                try {
                    dueDate = new Date(dueDateValue).toLocaleDateString();
                } catch(e) {
                    console.warn('Could not format date:', dueDateValue, e);
                    dueDate = String(dueDateValue);
                }
            }

            // Add status class
            const statusClass = getStatusClass(blocker.Status);

            row.append(`
                <td><a href="${blocker.issue_url || `https://benoveltyv3.atlassian.net/browse/${blocker['Issue key']}`}" target="_blank">${blocker['Issue key']}</a></td>
                <td>${blocker.Summary}</td>
                <td><span class="status-pill ${statusClass}">${blocker.Status}</span></td>
                <td>${dueDate}</td>
            `);

            tbody.append(row);
        });

        container.append(table);
    }
    
    /**
     * Create project completion chart
     */
    function createProjectCompletionChart(project) {
        // First ensure the container exists and has size
        const container = $('#project-completion-chart');
        if (container.length === 0) {
            console.error('Project completion chart container not found!');
            return;
        }
        
        // Make sure Plotly is available
        if (!ensurePlotly()) return;
        
        // Ensure the container has proper dimensions
        if (container.width() === 0 || container.height() === 0) {
            container.css({
                'min-height': '250px',
                'width': '100%',
                'display': 'block'
            });
        }
        
        // Calculate proper values
        const completed = project.completed_points || 0;
        const total = project.total_points || 0;
        const remaining = total > completed ? total - completed : 0;
        const percentage = project.completion_percentage !== undefined ? 
            project.completion_percentage : (total > 0 ? Math.round((completed / total) * 100) : 0);
            
        const data = [{
            values: [completed, remaining],
            labels: ['Completed', 'Remaining'],
            type: 'pie',
            hole: 0.7,
            marker: {
                colors: ['#10b981', '#e2e8f0']
            },
            textinfo: 'percent',
            hoverinfo: 'label+value'
        }];
        
        const layout = {
            title: 'Project Completion',
            height: 300,
            margin: {
                l: 0,
                r: 0,
                b: 30,
                t: 30,
                pad: 0
            },
            annotations: [{
                text: `${percentage}%`,
                font: {
                    size: 24,
                    color: '#334155'
                },
                showarrow: false,
                x: 0.5,
                y: 0.5
            }]
        };
        
        try {
            Plotly.newPlot('project-completion-chart', data, layout, {responsive: true});
            console.log('Project completion chart created successfully');
        } catch (error) {
            console.error('Error rendering project completion chart:', error);
            container.html('<div class="alert alert-danger">Failed to render chart. See console for details.</div>');
        }
    }
    
    /**
     * Create project resource allocation chart
     */
    function createProjectResourceAllocationChart(project) {
        // First ensure the container exists and has size
        const container = $('#project-resource-allocation-chart');
        if (container.length === 0) {
            console.error('Project resource allocation chart container not found!');
            return;
        }
        
        // Make sure Plotly is available
        if (!ensurePlotly()) return;
        
        // Ensure the container has proper dimensions
        if (container.width() === 0 || container.height() === 0) {
            container.css({
                'min-height': '250px',
                'width': '100%',
                'display': 'block'
            });
        }
        
        // Transform assignee distribution to arrays for the chart
        const assigneeDistribution = project.assignee_distribution || {};
        if (Object.keys(assigneeDistribution).length === 0) {
            container.html('<div class="alert alert-info">No resource allocation data available for this project.</div>');
            return;
        }
        
        const assignees = Object.keys(assigneeDistribution);
        const hours = assignees.map(assignee => assigneeDistribution[assignee]);
        
        // Generate colors for each assignee
        const colors = generateColorsArray(assignees.length);
        
        const data = [{
            x: assignees,
            y: hours,
            type: 'bar',
            marker: {
                color: colors
            },
            text: hours.map(h => h.toFixed(1) + ' hrs'),
            textposition: 'auto'
        }];
        
        const layout = {
            title: 'Resource Allocation',
            height: 300,
            margin: {
                l: 50,
                r: 20,
                b: 80,
                t: 30
            },
            yaxis: {
                title: 'Hours'
            },
            xaxis: {
                tickangle: -45
            }
        };
        
        try {
            Plotly.newPlot('project-resource-allocation-chart', data, layout, {responsive: true});
            console.log('Project resource allocation chart created successfully');
        } catch (error) {
            console.error('Error rendering project resource allocation chart:', error);
            container.html('<div class="alert alert-danger">Failed to render chart. See console for details.</div>');
        }
    }
    
    /**
     * Render project team members
     */
    function renderProjectTeamMembers(project) {
        const container = $('#project-team-members');
        container.empty();
        
        if (!project.team_members || project.team_members.length === 0) {
            container.append('<p class="text-muted">No team members assigned</p>');
            return;
        }
        
        project.team_members.forEach(member => {
            if (!member || member === 'undefined' || member === 'null') return;
            
            // Create initials for the avatar
            const initials = getInitials(member);
            
            const teamMember = $(`
                <div class="team-member">
                    <div class="avatar">${initials}</div>
                    <span>${member}</span>
                </div>
            `);
            
            container.append(teamMember);
        });
    }
    
    /**
     * Render project blockers list
     * @param {Object} project - Project data
     */
    function renderProjectBlockersList(project) {
        const container = $('#project-blockers-list');
        container.empty();
        
        // Get project blockers from current dashboard data
        if (!project.blockers) {
            container.append('<p class="text-muted">No blocker data available for projects</p>');
            return;
        }
        
        // Get blockers specific to this project
        const projectBlockers = project.blockers;

        if (!projectBlockers || projectBlockers.length === 0) {
            container.append('<p class="text-muted">No blockers found for this project</p>');
            return;
        }
        
        // Add summary counts at the top
        const totalBlockers = projectBlockers.length;
        const overdueBlockers = projectBlockers.filter(b => (b.blocker_type || b.blockerType) === 'overdue').length;
        const incompleteBlockers = totalBlockers - overdueBlockers;

        const summaryHtml = `
            <div class="blocker-summary mb-3">
                <span class="badge bg-secondary me-2">Total: ${totalBlockers}</span>
                <span class="badge bg-danger me-2">Overdue: ${overdueBlockers}</span>
                <span class="badge bg-warning text-dark">Incomplete: ${incompleteBlockers}</span>
            </div>
        `;

        container.append(summaryHtml);

        const table = $(`
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Summary</th>
                        <th>Assignee</th>
                        <th>Status</th>
                        <th>Due Date</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `);

        const tbody = table.find('tbody');

        projectBlockers.forEach(blocker => {
            // Extract blocker type or default to 'incomplete'
            const blockerType = blocker.blocker_type || blocker.blockerType || 'incomplete';
            const rowClass = blockerType === 'overdue' ? 'table-danger' : 'table-warning';
            const row = $(`<tr class="${rowClass}"></tr>`);

            // Format the due date
            let dueDate = 'Not set';
            const dueDateValue = blocker['Due date'] || blocker.due_date || blocker.dueDate;
            if (dueDateValue) {
                try {
                    dueDate = new Date(dueDateValue).toLocaleDateString();
                } catch(e) {
                    console.warn('Could not format date:', dueDateValue, e);
                    dueDate = String(dueDateValue);
                }
            }

            // Add status class
            const statusClass = getStatusClass(blocker.Status);

            row.append(`
                <td><a href="${blocker.issue_url || `https://benoveltyv3.atlassian.net/browse/${blocker['Issue key']}`}" target="_blank">${blocker['Issue key']}</a></td>
                <td>${blocker['Summary']}</td>
                <td>${blocker.Assignee || 'Unassigned'}</td>
                <td><span class="status-pill ${statusClass}">${blocker.Status}</span></td>
                <td>${dueDate}</td>
            `);

            tbody.append(row);
        });

        container.append(table);
    }
    
    /**
     * Clear assignee filter
     */
    $('#clear-assignee-filter').click(function() {
        // Remove active class from all assignee bubbles
        $('.assignee-bubble').removeClass('active');
        
        // Hide assignee details
        $('#assignee-detail-view').addClass('d-none');
        $('#selected-assignee-info').addClass('d-none');
    });
    
    /**
     * Clear project filter
     */
    $('#clear-project-filter').click(function() {
        // Remove active class from all project bubbles
        $('.project-bubble').removeClass('active');
        
        // Hide project details
        $('#project-detail-view').addClass('d-none');
        $('#selected-project-info').addClass('d-none');
    });
    
    /**
     * Helper function to get workload class based on total points
     */
    function getWorkloadClass(totalPoints) {
        if (totalPoints <= 20) {
            return 'workload-low';
        } else if (totalPoints <= 40) {
            return 'workload-medium';
        } else {
            return 'workload-high';
        }
    }
    
    /**
     * Helper function to get completion class based on completion percentage
     */
    function getCompletionClass(completionPercentage) {
        if (completionPercentage >= 80) {
            return 'completion-high';
        } else if (completionPercentage >= 50) {
            return 'completion-medium';
        } else {
            return 'completion-low';
        }
    }
    
    /**
     * Helper function to get status class based on status
     */
    function getStatusClass(status) {
        if (!status) return 'status-todo';
        
        status = status.toLowerCase();
        if (status.includes('done')) {
            return 'status-done';
        } else if (status.includes('progress') || status.includes('doing')) {
            return 'status-progress';
        } else if (status.includes('review')) {
            return 'status-review';
        } else if (status.includes('block')) {
            return 'status-blocked';
        } else {
            return 'status-todo';
        }
    }
    
    /**
     * Helper function to generate initials from a name
     */
    function getInitials(name) {
        if (!name) return '?';
        
        const parts = name.split(' ');
        if (parts.length === 1) {
            return parts[0].charAt(0).toUpperCase();
        } else {
            return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
        }
    }
    
    /**
     * Helper function to generate an array of colors
     */
    function generateColorsArray(count) {
        const baseColors = [
            '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', 
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
        ];
        
        // If we need more colors than the base array, repeat them
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        
        return colors;
    }
    
    /**
     * Ensure that Plotly is available before attempting to render charts
     * @returns {boolean} - True if Plotly is available, false otherwise
     */
    function ensurePlotly() {
        if (typeof Plotly === 'undefined') {
            console.error('Plotly.js is not loaded! Charts will not render correctly.');
            
            // Add a message to the chart containers
            ['completion-chart', 'velocity-chart', 'billable-chart', 'capacity-chart'].forEach(id => {
                const container = $(`#${id}`);
                if (container.length > 0) {
                    container.html('<div class="alert alert-danger">Unable to load charts. Plotly.js library is missing.</div>');
                }
            });
            
            return false;
        }
        
        return true;
    }
    
    /**
     * Handle archive current sprint button click
     */
    $('#archive-current').click(function() {
        if (!currentDashboardData) {
            alert('Please generate a dashboard first.');
            return;
        }
        
        $.ajax({
            url: '/archive-sprint',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ sprint_index: currentSprintIndex }),
            success: function(response) {
                if (response.status === 'success') {
                    alert('Current sprint archived successfully.');
                    
                    // Reload sprints to update dropdown
                    loadArchivedSprints();
                } else {
                    alert('Error archiving sprint: ' + response.message);
                }
            },
            error: function() {
                alert('Error archiving sprint. Please try again.');
            }
        });
    });
    
    /**
     * Load archived sprints from the server
     */
    function loadArchivedSprints() {
        $.ajax({
            url: '/get-archived-sprints',
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    const reports = response.archived_sprints || [];

                    // Populate sprint dropdown with archived sprints (for quick selection)
                    populateSprintDropdown(reports);

                    // Update sidebar list
                    const $list = $('#archived-sprints-list');
                    $list.empty();

                    if (reports.length === 0) {
                        $list.html('<p class="text-muted">No archived sprints yet.</p>');
                    } else {
                        reports.forEach(r => {
                            const item = $('<div class="archived-item mb-2"></div>');
                            item.text(`${r.sprint_name} (${r.date_archived})`);

                            const btn = $('<button class="btn btn-sm btn-outline-primary ms-2">View</button>');
                            btn.click(function() { loadArchivedSprint(r.id); });
                            item.append(btn);

                            $list.append(item);
                        });
                    }
                } else {
                    console.error('Error loading archived sprints:', response.message);
                }
            },
            error: function() {
                console.error('Error loading archived sprints');
            }
        });
    }

    /**
     * Fetch a specific archived sprint and display it
     */
    function loadArchivedSprint(archiveId) {
        $.ajax({
            url: `/get-archived-sprint/${archiveId}`,
            type: 'GET',
            success: function(response) {
                if (response.status === 'success' && response.archived_sprint) {
                    const sprint = response.archived_sprint;
                    const dashboard = sprint.dashboard;
                    if (dashboard) {
                        currentDashboardData = dashboard;
                        updateDashboard(dashboard);
                    } else if (sprint.metrics) {
                        updateDashboard(generateDashboardFromMetrics(sprint.metrics));
                    }
                    if (sprint.assignees) {
                        renderAssigneeBubbles(sprint.assignees);
                    }
                    if (sprint.projects) {
                        renderProjectBubbles(sprint.projects);
                        projectDataMap = {};
                        sprint.projects.forEach(p => { projectDataMap[p.name] = p; });
                        populateWorkloadProjectBubbles(sprint.projects);
                    }
                } else {
                    console.error('Error loading archived sprint:', response.message);
                }
            },
            error: function() {
                console.error('Error loading archived sprint');
            }
        });
    }

    // Helper to build minimal dashboard if only metrics are available
    function generateDashboardFromMetrics(metrics) {
        return {
            metrics: metrics,
            completion_chart: null,
            billable_chart: null,
            capacity_chart: null,
            velocity_chart: null,
            projected_capacity: null
        };
    }

    /**
     * Export the dashboard using the browser's PDF printer
     */
    $('#export-pdf').click(function() {
        const element = document.getElementById('dashboard-container');
        if (!element || $(element).hasClass('d-none')) {
            alert('Please generate a dashboard first.');
            return;
        }

        window.print();
    });
    
    // Responsive tweaks for filter bubbles, chart containers, and metric cards
    function applyMobileResponsiveTweaks() {
        const isMobile = window.innerWidth < 768;
        // Filter bubbles
        if (isMobile) {
            $('.filter-bubble').css({'display': 'block', 'margin-bottom': '10px', 'width': '100%'});
        } else {
            $('.filter-bubble').css({'display': '', 'margin-bottom': '', 'width': ''});
        }
        // Chart containers
        $('.chart-container, .card, .metric-card').css({
            'width': isMobile ? '100%' : '',
            'min-width': isMobile ? '0' : '',
            'overflow-x': isMobile ? 'auto' : ''
        });
        // Forecast row spacing
        $('.forecast-row').css({
            'margin-left': isMobile ? '0' : '',
            'margin-right': isMobile ? '0' : ''
        });
    }
    
    // Call on load and on resize
    applyMobileResponsiveTweaks();
    $(window).on('resize', applyMobileResponsiveTweaks);

    // No additional handlers needed: bubble clicks update the table
});
