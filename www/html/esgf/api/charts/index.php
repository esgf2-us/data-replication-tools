<?php
    header("Access-Control-Allow-Origin: *");
    header("Content-type: application/json;charset=utf-8");

    include("../../../../../esgf.inc");
    $db = pg_connect("host=$esgf_server dbname=$esgf_db user=$esgf_user password=$esgf_pass");

    $request_array = explode('/', $_SERVER['REQUEST_URI']);
    $set = end($request_array);
    while ($set != 'api')
        $set = prev($request_array);
    $set = prev($request_array);

    date_default_timezone_set('UTC');
    if (isset($_GET['today']) and strtotime($_GET['today']))
        $now = "timestamp '" . $_GET['today'] . "'";
    else
        $now = 'now()';

    $summary = array();
    $query = 'SELECT destination, sum(bytes_transferred) from transfer group by destination';
    $out = pg_query($query);
    while ($row = pg_fetch_row($out)) {
        $summary += array($row[0] => is_null($row[1]) ? 0 : (int) $row[1]);
    }

    http_response_code(200);
    echo json_encode($summary);
?>
