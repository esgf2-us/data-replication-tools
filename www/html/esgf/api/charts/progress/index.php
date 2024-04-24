<?php
    header("Access-Control-Allow-Origin: *");
    header("Content-type: application/json;charset=utf-8");

    include("../../../../../../esgf.inc");
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

    $divider = 1024 * 1024 * 1024 * 1024;
    $response = array();
    $sites = array('LLNL', 'ALCF', 'OLCF');
    foreach ($sites as $destination) {
        if ($destination == 'LLNL')
            continue;
        foreach ($sites as $source) {
            if ($source == $destination)
                continue;
            $transfers = array();
            $transfer = array('2022-02-12 00:00:00', 0);
            array_push($transfers, $transfer);
            $query = 'select date_trunc(\'hour\',time), sum(bytes_transferred) from event where description=\'progress\' and source=\'' . $source . '\' and destination=\'' . $destination . '\' group by date_trunc(\'hour\',time) order by date_trunc(\'hour\',time);';
            $out = pg_query($query);
            while ($row = pg_fetch_row($out)) {
                $transfer = array($row[0], ((int) $row[1]) / $divider);
                array_push($transfers, $transfer);
            }
            array_push($response, array(
                'source' => $source,
                'destination' => $destination,
                'transfers' => $transfers)
            );
        }
    }

    http_response_code(200);
    echo json_encode($response);
?>
