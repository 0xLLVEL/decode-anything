<?php

final class Greeter
{
    public static $count = 1;
    public $name = 'world';
    public ?DateTimeImmutable $created;
    public readonly string $id;
    public int|string|null $value;
    public Countable&ArrayAccess $both;
    public (Countable&ArrayAccess)|Traversable|null $either;

    public function greet(string $greeting = 'hello'): int|string
    {
        return 1;
    }

    public function collect(Countable&ArrayAccess $items): (Countable&ArrayAccess)|Traversable
    {
        return 1;
    }
}
