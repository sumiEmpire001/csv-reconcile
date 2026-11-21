# Embedded C++ companion

The existing Python implementation remains unchanged. This C++11 fixed-capacity algorithm is a distinct, deliberately limited embedded companion.

Bounded exact-string key/value reconciliation for device configuration snapshots. Unlike Python's SQLite-backed CSV engine it does not parse CSV, support composite keys, Unicode normalization or Decimal equality. Duplicate keys latch a fault rather than reporting duplicate groups; never use for financial reconciliation.

## Host verification

```sh
cmake -S cpp -B build
cmake --build build
ctest --test-dir build --output-on-failure
python -m unittest discover -s tests -v
```

The C++ source includes host assertions when built with EMBEDDED_TEST. GitHub Actions runs GCC and Clang host builds; existing Python CI remains separate. **No AVR/ESP32 board build or physical device test is claimed.**

## Board integration and safety

For Arduino Uno (AVR, 2 KB SRAM), choose small template capacities and measure memory use; for ESP32, select capacities according to available heap and task stack. Compile the core as C++11 in the board toolchain after separating the optional test main. Do not allocate large instances on a small stack. All input must be bounded and validated. A latched fault requires an explicit reset. This is not an actuator driver; outputs must never directly energize pumps, relays, motors or other equipment. Add independent interlocks, watchdog, emergency stop, brownout handling and sensor fault detection before physical deployment.
