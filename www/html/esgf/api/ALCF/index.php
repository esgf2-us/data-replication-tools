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

    $query = 'SELECT dataset,source,requested,completed,status,directories,files,files_transferred,bytes_transferred,faults,rate FROM transfer WHERE destination=\'ALCF\' order by dataset';
    $out = pg_query($query);
    $transfers = array();
    while ($row = pg_fetch_assoc($out)) {
        extract($row);
        $transfer = array(
            'dataset' => $dataset,
            'source' => is_null($source) ? '' : $source ,
            'requested' => is_null($requested) ? '' : $requested,
            'completed' => is_null($completed) ? '' : $completed,
            'status' => is_null($status) ? '' : $status,
            'directories' => is_null($directories) ? '' : (int) $directories,
            'files' => is_null($files) ? '' : (int) $files,
            'files_transferred' => is_null($files_transferred) ? '' : (int) $files_transferred,
            'bytes' => is_null($bytes_transferred) ? '' : (int) $bytes_transferred,
            'status' => is_null($status) ? '' : $status,
            'faults' => is_null($faults) ? '' : (int) $faults,
            'rate' => is_null($rate) ? '' : (int) $rate,
        );
        array_push($transfers, $transfer);
    }

    http_response_code(200);
    echo json_encode($transfers);
?>
