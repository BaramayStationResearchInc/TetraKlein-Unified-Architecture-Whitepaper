use snforge_std::{declare, ContractClassTrait}; // Removed DeclareResultTrait
use tetraklein_stark::{ITetraValidatorDispatcher, ITetraValidatorDispatcherTrait};

mod data_input; 
use data_input::get_test_data;

#[test]
fn test_stark_integrity_lock() {
    let contract_class = match declare("TetraValidator").unwrap() {
        snforge_std::DeclareResult::Success(class) => class,
        _ => panic!("Deployment Failed"),
    };

    let (contract_address, _) = contract_class.deploy(@array![]).unwrap();
    let dispatcher = ITetraValidatorDispatcher { contract_address };

    let witness_y = get_test_data();
    let initial_acc: felt252 = 0xDEADBEEF;
    
    let final_acc = dispatcher.check_segment(initial_acc, 0, witness_y);
    
    assert(final_acc != 0, 'ZERO_ACC_ERROR');
}
