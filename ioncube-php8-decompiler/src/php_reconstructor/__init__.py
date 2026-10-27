"""php_reconstructor -- reconstruct PHP source from PHP 8.1 opcode dumps.

Pipeline: JSON opcode dump -> normalized opcode model -> IR (basic blocks /
CFG) -> PHP AST -> emitted PHP source.
"""

__version__ = "0.1.0"
