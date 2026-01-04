// 1. The Interface (Public and in the Crate Root)
#[starknet::interface]
pub trait ITetraValidator<TContractState> {
    fn check_segment(
        self: @TContractState, 
        initial_acc: felt252, 
        start_step: u64, 
        witness_y: Array<u8>
    ) -> felt252;
}

// 2. The Contract
#[starknet::contract]
pub mod TetraValidator {
    // Explicitly import the trait from the crate root
    use crate::ITetraValidator;

    const ALPHA: felt252 = 1315423911;

    #[storage]
    struct Storage {}

    #[abi(embed_v0)]
    impl TetraValidatorImpl of ITetraValidator<ContractState> {
        fn check_segment(
            self: @ContractState, 
            initial_acc: felt252, 
            start_step: u64, 
            witness_y: Array<u8>
        ) -> felt252 {
            let mut acc = initial_acc;
            let mut step = start_step;
            
            let mut i = 0;
            let len = witness_y.len();
            
            loop {
                if i >= len {
                    break;
                }
                
                let y = *witness_y.at(i);
                
                // TetraKlein Transition: acc = (ALPHA * acc) + y + step
                acc = (ALPHA * acc) + y.into() + step.into();
                
                step += 1;
                i += 1;
            };
            acc
        }
    }
}
