// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IStablecoinDEX {
    function swapExactAmountIn(
        address tokenIn,
        address tokenOut,
        uint128 amountIn,
        uint128 minAmountOut
    ) external returns (uint128 amountOut);
}

contract BatchOperations {
    /**
     * @notice Execute approve + swap in one transaction
     * @param token Token to approve and swap
     * @param dex DEX contract address
     * @param tokenOut Output token address
     * @param amount Amount to swap
     * @param minOut Minimum output amount
     */
    function approveAndSwap(
        address token,
        address dex,
        address tokenOut,
        uint128 amount,
        uint128 minOut
    ) external returns (uint128) {
        // Transfer tokens from user to this contract
        require(
            IERC20(token).transferFrom(msg.sender, address(this), amount),
            "Transfer failed"
        );
        
        // Approve DEX to spend tokens
        require(
            IERC20(token).approve(dex, amount),
            "Approve failed"
        );
        
        // Execute swap
        uint128 amountOut = IStablecoinDEX(dex).swapExactAmountIn(
            token,
            tokenOut,
            amount,
            minOut
        );
        
        // Transfer output tokens back to user
        require(
            IERC20(tokenOut).transfer(msg.sender, amountOut),
            "Output transfer failed"
        );
        
        return amountOut;
    }
    
    /**
     * @notice Execute multiple transfers in one transaction
     * @param token Token to transfer
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts to transfer
     */
    function batchTransfer(
        address token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        require(recipients.length == amounts.length, "Length mismatch");
        require(recipients.length <= 10, "Too many transfers");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            require(
                IERC20(token).transferFrom(msg.sender, recipients[i], amounts[i]),
                "Transfer failed"
            );
        }
    }
    
    /**
     * @notice Execute multiple swaps in one transaction
     * @param dex DEX contract address
     * @param tokensIn Array of input tokens
     * @param tokensOut Array of output tokens
     * @param amounts Array of amounts to swap
     * @param minOuts Array of minimum output amounts
     */
    function batchSwap(
        address dex,
        address[] calldata tokensIn,
        address[] calldata tokensOut,
        uint128[] calldata amounts,
        uint128[] calldata minOuts
    ) external returns (uint128[] memory) {
        require(tokensIn.length == tokensOut.length, "Length mismatch");
        require(tokensIn.length == amounts.length, "Length mismatch");
        require(tokensIn.length == minOuts.length, "Length mismatch");
        require(tokensIn.length >= 2 && tokensIn.length <= 5, "Invalid count");
        
        uint128[] memory amountsOut = new uint128[](tokensIn.length);
        
        for (uint256 i = 0; i < tokensIn.length; i++) {
            // Transfer tokens from user to this contract
            require(
                IERC20(tokensIn[i]).transferFrom(msg.sender, address(this), amounts[i]),
                "Transfer failed"
            );
            
            // Approve DEX to spend tokens
            require(
                IERC20(tokensIn[i]).approve(dex, amounts[i]),
                "Approve failed"
            );
            
            // Execute swap
            amountsOut[i] = IStablecoinDEX(dex).swapExactAmountIn(
                tokensIn[i],
                tokensOut[i],
                amounts[i],
                minOuts[i]
            );
            
            // Transfer output tokens back to user
            require(
                IERC20(tokensOut[i]).transfer(msg.sender, amountsOut[i]),
                "Output transfer failed"
            );
        }
        
        return amountsOut;
    }
}
