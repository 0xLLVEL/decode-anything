<?php

final class Greeter
{
    public static $count = 1;
    public $name = 'world';
    public ?DateTimeImmutable $created;
    public readonly string $id;
    public int|string|null $value;

    public function greet($greeting = 'hello')
    {
        return 1;
    }
}
