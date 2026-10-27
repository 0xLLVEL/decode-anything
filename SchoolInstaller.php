<?php

namespace SpondonIt\SchoolService\Installers;

use App\User;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\ValidationException;
use SpondonIt\Service\Contracts\AppInstallerInterface;
use SpondonIt\Service\Services\DatabaseService;
use App\Models\SmStaff;
use App\Models\SmSchool;
use App\Models\SmGeneralSettings;

class SchoolInstaller implements AppInstallerInterface
{
    public function __construct(
            protected DatabaseService $databaseService,
    ) {}

    /**
     * Run the full app-specific installation.
     *
     * @param array{email: string, password: string, seed?: bool} $params
     */
    public function install(array $params): void
    {
        try {
            $this->makeAdmin($params);

            $this->databaseService->seed(! empty($params['seed']));

            Artisan::call('key:generate', ['--force' => true]);

            updateEnvFile([
                    'APP_ENV' => 'production',
                    'APP_DEBUG' => 'false',
            ]);
        } catch (\Exception $e) {
            Storage::delete(['.user_email', '.user_pass']);

            throw ValidationException::withMessages(['message' => $e->getMessage()]);
        }
    }

    /**
     * Create or update the initial admin user.
     *
     * @param array{email: string, password: string} $params
     */
    public function makeAdmin(array $params): mixed
    {
        try {

            $user = User::find(1);
            if(!$user){
                $user = new User();
            }

            $user->email = gv($params, 'email');
            $user->role_id = 1;
            $user->password = bcrypt(gv($params, 'password', 'abcd1234'));
            $user->save();

            $staff = SmStaff::first();
            if (!$staff) {
                $staff = new SmStaff();
            }
            $staff->user_id  = $user->id;
            $staff->first_name  = 'System';
            $staff->last_name  = 'Administrator';
            $staff->full_name  = 'System Administrator';
            $staff->email  = $user->email ;
            $staff->save();

            $setting =  SmGeneralSettings::first();
            $setting->email = $user->email;
            $setting->system_purchase_code = Storage::get('.access_code');
            $setting->system_activated_date = date('Y-m-d');
            $setting->system_domain = app_url();
            $setting->save();

            $school = SmSchool::first();
            $school->email = $user->email;
            $school->save();

            return $user;
        } catch(\Exception $e){
            $this->databaseService->rollback();
            throw ValidationException::withMessages(['message' => $e->getMessage()]);
        }
    }
}
