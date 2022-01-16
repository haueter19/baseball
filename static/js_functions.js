
$.fn.owners_chart = function(x_var, y_var){
    let x_data = [];
    let y_data = [];
    $.each(owners, function(i, v){
        x_data.push(v[x_var]);
        y_data.push(v[y_var]);
    })
    owners_data = [
        {
            type: 'bar',
            x:x_data,
            y:y_data,
            
        }
    ]
    layout = {title: "Title", height: 400, width: 1000, margin: {t:30}},
    Plotly.newPlot("owners_chart", owners_data, layout, {displayModeBar: false})    
}
$.fn.z_players = function(){
    let x_data = [];
    let y_data = [];
    let hover_data = [];
    let color_map = [];
    var j = 0;
    $.each(data, function(i, v){
        if (j<175){
            x_data.push(j);
            y_data.push(data[i]['z']);
            hover_data.push(data[i]['Name']);
            if (data[i]['Owner']){
                color_map.push('gray');
            } else {
                color_map.push('blue');
            }
        }
        j += 1
    })

    z_scatter_data = [
        {
            type: 'scatter',
            x:x_data,
            y:y_data,
            text:hover_data,
            mode:'markers',
            marker: { color: color_map }
            
        }
    ]
    layout = {title: "Z List", height: 400, width: 1000, margin: {t:30}},
    Plotly.newPlot("z_players_chart", z_scatter_data, layout, {displayModeBar: false})
}
$.fn.create_radar_chart = function(selected){
    $("#projected_stats_table tr").hide();
    $("#projected_stats_table tr:first").show();
    $("#"+selected).show();
    $.each(data, function(i, v) {
            if (v.playerid == selected) {
                selected_index = i
                return;
            }
        });
    $("#radar_chart_player_name").text(data[selected_index]['Name']);
    radar_data = [{
            type: 'scatterpolar',
            r: [data[selected_index]['zBA'], data[selected_index]['zHR'], data[selected_index]['zR'], data[selected_index]['zRBI'], data[selected_index]['zSB'], data[selected_index]['zBA']],
            theta: ['BA','HR','R', 'RBI', 'SB', 'BA'],
            fill: 'toself'
            }]

            layout = {
                height: 300,
                polar: {
                    radialaxis: {
                    visible: true,
                    range: [-3, 3]
                    },
                margin: { l:0, r:0, t:0, b:0, pad:0}
            },
            showlegend: false
        }
    Plotly.newPlot("radar_chart", radar_data, layout, {displayModeBar: false})
}
$(document).ready(function(){
    $("#projected_stats_table tr").hide();
    $("#projected_stats_table tr:first").show();
    $("input[name='playerid']").on('focusout', function(e){
        var selected = $(this).val();
        $(this).create_radar_chart(selected);
    });
    $("#button").click(function(){
        var v = $("#player_list").val();
        $.get("/fantasy/draft/"+v, function(data, status){
            alert("Data: " + data + "\nStatus: " + status);
        });
    });                
    $("#rosterTable").on("click", "td", function() {
        var p_name = $(this).text();
        $.each(data, function(i, v) {
            if (v.Name == p_name) {
                var tr_id = v.playerid
                $("#player_select").val(tr_id);
                $(this).create_radar_chart(tr_id);
                return tr_id;
            }
        });
    });
    $("#drafted_scroll").on("click", "td", function() {
        var p_name = $(this).text();
        $.each(data, function(i, v) {
            if (v.Name == p_name) {
                var tr_id = v.playerid
                $("#player_select").val(tr_id);
                $(this).create_radar_chart(tr_id);
                return tr_id;
            }
        });
    });
    $.fn.z_players();
    $.fn.owners_chart('Owner', '$ Left');
})
