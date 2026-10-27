<?php

namespace SpondonIt\Service\Console\Commands;

use Illuminate\Database\Console\Migrations\BaseCommand;
use Illuminate\Support\Collection;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Console\Commands\MigrateStatusCommand.php
 */

class MigrateStatusCommand extends BaseCommand {
    protected $signature = 'spondonit:migrate-status';
    protected $description = 'Command description';
    protected $migrator;

    public function __construct() {
        $this->migrator = app()->make('migrator');
        parent::__construct();
    }

    public function handle() {
        if (!$this->migrator->repositoryExists()) {
            return false;
        }
        $ran = $this->migrator->getRepository()->getRan();
        $batches = $this->migrator->getRepository()->getMigrationBatches();
        $migrations = $this->getStatusFor($ran, $batches);
        if (0 < count($migrations)) {
            return !in_array(false, $migrations->toArray());
        } else {
            return false;
        }
    }

    protected function getStatusFor(array $ran, array $batches) {
        return Collection::make($this->getAllMigrationFiles())->map(function ($migration) use ($ran) {
            $migrationName = $this->migrator->getMigrationName($migration);
            return in_array($migrationName, $ran);
        });
    }

    protected function getAllMigrationFiles() {
        return $this->migrator->getMigrationFiles($this->getMigrationPaths());
    }
}
