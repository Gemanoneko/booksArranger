# Books Arranger next version requests

## Hide unavailable databases from installer discovery

Reported by Sergei while installing 0.28.0 on November 13, 2026. The database chooser listed the current catalog alongside a default path marked “Location unavailable,” making it look like there were two databases.

For the next version, omit unavailable locations from automatic discovery. Keep Browse available and explain how to choose a database if no available catalog is found. If the user explicitly browses to a file that cannot be opened, explain why. If setup cannot access the catalog configured for the installation being upgraded, stop and ask the user to restore access or explicitly select a different catalog.

## Keep staging ownership accurate across job updates

On November 13, 2026, the live relocation inventory stopped at “Staging marker differs from its catalog producer.” Of 87 mismatches, 82 match an exact immutable closed or retired attempt manifest. The current job manifest changed its destination or metadata after those markers were created. Completed series retagging is one writer of the current manifest. Five older trees lack a matching working-attempt row. Those trees contain 18 files totaling 270,336 bytes. The catalog still refers to 13 files in one of these trees through its cleanup preservation records and records an authorization for the tree. The files are still used as preservation evidence.

Use the exact matching historical attempt and its native proof for migration inventory. Carry forward preserved legacy evidence using its existing catalog references and verified file identities without treating it as eligible for deletion. Make new job updates preserve the ownership link. When retirement completes, use the existing finite native cleanup path to retire empty staging shells and markers after active work, publication, retained recovery, and historical references have been checked. Persist enough proof to resume cleanup after an interruption and identify the exact files held when ownership cannot be established. Preserve unbound legacy files for separate review.

Acceptance checks should cover a closed attempt followed by a destination or metadata update, an interrupted cleanup followed by restart, and preservation of a marker with conflicting or missing proof. Verify that pending jobs, retained recovery files, published outputs, and book libraries are unaffected. Test a valid historical marker in the migration inventory without changing its original bytes.

The full source inventory also found 8,033 entries outside the current migration ownership rules. They include 6,462 cover-cache files, 1,528 audio-staging files and 15 attempt directories, 25 chapter-repair files and two directories, and the empty series-retag staging parent. Identify the producer and retention rules for each group. Keep unclassified files during migration; add a verified preservation path that keeps their bytes and recorded references without granting cleanup authority. Verify that retained files stay excluded from source retirement and that rollback can distinguish old and new writes. Census evidence is in `I:\Books Arranger\Backups\ai-projects-cutover\finite-unknowns.supervisor.json`.
