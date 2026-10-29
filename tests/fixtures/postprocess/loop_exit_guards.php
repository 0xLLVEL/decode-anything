<?php

function merge_guard(array $items): void
{
    foreach ($items as $item) {
        if ($item === '') {
            goto label_10;
        }
        echo $item;
    }
    label_10:
    return;
}

function guard_skips_trailing_statement(array $items): void
{
    foreach ($items as $item) {
        if ($item === '') {
            goto label_20;
        }
        echo $item;
    }
    echo 'after';
    label_20:
    return;
}

function closure_chain(array $items): callable
{
    $fn = function (bool $skip) use ($items) {
        foreach ($items as $item) {
            if ($skip) {
                goto label_30;
            }
            echo $item;
        }
        label_30:
        goto label_40;
        label_40:
        return true;
    };
    return $fn;
}
